"""
CV Processor — Extract structured info from PDF CVs using Ollama.

Directory structure expected:
  cv/              → input CVs
  processed_cv/    → moved after success
  insights/        → skills.txt, career_objective.txt, projects.txt,
                     processlog.txt, all_candidates.json
"""
import pdfplumber

import os
import json
import shutil
import requests
from datetime import datetime
from pathlib import Path
import fitz  # PyMuPDF

# ── Try pdfplumber first, fallback to PyMuPDF ──────────────────────────────
try:
    PDF_BACKEND = "pdfplumber"
except ImportError:
    try:
        PDF_BACKEND = "pymupdf"
    except ImportError:
        raise ImportError("Install pdfplumber or PyMuPDF: pip install pdfplumber  OR  pip install pymupdf")

# ── Config ──────────────────────────────────────────────────────────────────
CV_DIR              = Path("cv")
PROCESSED_DIR       = Path("processed_cv")
INSIGHTS_DIR        = Path("insights")
LOG_FILE            = INSIGHTS_DIR / "processlog.txt"
SKILLS_FILE         = INSIGHTS_DIR / "skills.txt"
CAREER_OBJ_FILE     = INSIGHTS_DIR / "career_objective.txt"
PROJECTS_FILE       = INSIGHTS_DIR / "projects.txt"
ALL_CANDIDATES_FILE = INSIGHTS_DIR / "all_candidates.json"   # ← combined file

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "mistral:latest"
# MODEL       = "qwen3.5:4b"  # specify a version for stability


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def ensure_dirs() -> None:
    """Create output directories if they don't exist."""
    for d in [CV_DIR, PROCESSED_DIR, INSIGHTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def log(message: str, also_print: bool = True) -> None:
    """Append a timestamped line to processlog.txt."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}]  {message}"
    if also_print:
        print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_divider(char: str = "─", length: int = 55) -> None:
    """Print and log a plain divider line (no timestamp)."""
    line = char * length
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# 1. PDF TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract full text from every page of a PDF.
    Returns empty string on failure (corrupt / empty file).
    """
    try:
        if PDF_BACKEND == "pdfplumber":
            with pdfplumber.open(pdf_path) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip()

        else:  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            pages = [str(doc[i].get_text()) for i in range(len(doc))]
            doc.close()
            return "\n".join(pages).strip()

    except Exception as e:
        log(f"❌  PDF extraction failed for {pdf_path.name}: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# 2. LLM CALL (Ollama)
# ═══════════════════════════════════════════════════════════════════════════

EXTRACTION_PROMPT_TEMPLATE = """
You are a CV parser. Extract the following fields from the CV text below.
Respond ONLY with a valid JSON object — no explanation, no markdown fences.

Fields to extract:
- full_name        (string, or "UNKNOWN" if not found)
- email            (string, or "")
- career_objective (string, or "")
- skills           (list of strings)
- projects         (list of objects with keys: name, details)
- work_experience  (list of objects with keys: company, role, duration, description)
- education        (list of objects with keys: institution, degree, year)

CV TEXT:
"""

def call_llm(cv_text: str) -> str:
    """
    Send CV text to Ollama and return the raw response string.
    Raises on connection / HTTP errors.
    """
    prompt = EXTRACTION_PROMPT_TEMPLATE + cv_text[:12000]

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0}
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


# ═══════════════════════════════════════════════════════════════════════════
# 3. PARSE LLM OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def parse_llm_output(raw: str) -> dict | None:
    """
    Parse the LLM's JSON response into a Python dict.
    Returns None if parsing fails.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(cleaned)
        if not data.get("full_name"):
            data["full_name"] = "UNKNOWN"
        return data
    except json.JSONDecodeError as e:
        log(f"❌  JSON parse error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 4. SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════

def save_json(data: dict, cv_path: Path) -> None:
    """Save extracted data as individual JSON in processed_cv/."""
    out_path = PROCESSED_DIR / (cv_path.stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"💾  Individual JSON saved → {out_path}")


def append_to_all_candidates(data: dict, cv_filename: str) -> None:
    """
    Append this candidate's data into insights/all_candidates.json.
    The file holds a JSON array — we load, append, and rewrite atomically.
    """
    candidates: list = []

    if ALL_CANDIDATES_FILE.exists():
        try:
            candidates = json.loads(ALL_CANDIDATES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            candidates = []   # start fresh if file is corrupt

    entry = {"_source_file": cv_filename, **data}
    candidates.append(entry)

    with open(ALL_CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    log(f"📋  Appended to all_candidates.json  (total so far: {len(candidates)})")


def update_skills(skills: list[str]) -> None:
    """Append unique skills to insights/skills.txt."""
    existing: set[str] = set()
    if SKILLS_FILE.exists():
        existing = {
            line.strip().lower()
            for line in SKILLS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    new_skills = [s for s in skills if s.strip().lower() not in existing]
    if new_skills:
        with open(SKILLS_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(new_skills) + "\n")
        log(f"🛠️   {len(new_skills)} new skill(s) added to skills.txt")
    else:
        log("🛠️   No new skills to add.")


def update_career_objective(name: str, email: str, objective: str) -> None:
    """Append candidate's career objective block to insights/career_objective.txt."""
    block = f"{name} ({email})\n{objective}\n\n"
    with open(CAREER_OBJ_FILE, "a", encoding="utf-8") as f:
        f.write(block)
    log("🎯  Career objective appended.")


def update_projects(name: str, projects: list[dict]) -> None:
    """Append all projects from this candidate to insights/projects.txt."""
    if not projects:
        log("📁  No projects found for this candidate.")
        return
    with open(PROJECTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"=== Projects from: {name} ===\n")
        for p in projects:
            proj_name = p.get("name", "Unnamed Project")
            details   = p.get("details", "No details provided.")
            f.write(f"\n  Project : {proj_name}\n")
            f.write(f"  Details : {details}\n")
        f.write("\n")
    log(f"📁  {len(projects)} project(s) saved to projects.txt")


def save_outputs(data: dict, cv_path: Path) -> None:
    """Orchestrate all file-write operations for a single CV."""
    save_json(data, cv_path)
    append_to_all_candidates(data, cv_path.name)
    update_skills(data.get("skills", []))
    update_career_objective(
        data.get("full_name", ""),
        data.get("email", ""),
        data.get("career_objective", "")
    )
    update_projects(data.get("full_name", ""), data.get("projects", []))


# ═══════════════════════════════════════════════════════════════════════════
# 5. PROCESS A SINGLE CV
# ═══════════════════════════════════════════════════════════════════════════

def process_single_cv(cv_path: Path, index: int, total: int) -> bool:
    """
    Full pipeline for one CV file.
    Returns True on success, False on any failure.
    """
    remaining_after = total - index
    log(f"📄  File       : {cv_path.name}")
    log(f"📊  Progress   : {index}/{total}  |  Remaining after this: {remaining_after}")
    start = datetime.now()

    # Step 1: Extract text
    log("📝  Step 1/5  → Extracting text from PDF …")
    text = extract_text_from_pdf(cv_path)
    if not text:
        log("⚠️   Empty or unreadable PDF. Skipping.")
        return False

    # Step 2: Call LLM
    log("🤖  Step 2/5  → Sending to Ollama …")
    try:
        raw_response = call_llm(text)
    except requests.RequestException as e:
        log(f"❌  Ollama request failed: {e}")
        return False

    # Step 3: Parse response
    log("🔍  Step 3/5  → Parsing LLM response …")
    data = parse_llm_output(raw_response)
    if data is None:
        log("❌  Could not parse LLM output. Skipping.")
        return False

    # Step 4: Guard — name must not be UNKNOWN
    if data.get("full_name", "UNKNOWN").upper() == "UNKNOWN":
        log("⚠️   Name is UNKNOWN — file will NOT be moved.")
        return False

    log(f"✅  Candidate  : {data['full_name']}  |  Email: {data.get('email', 'N/A')}")

    # Step 5: Save all outputs
    log("💾  Step 4/5  → Saving outputs …")
    try:
        save_outputs(data, cv_path)
    except Exception as e:
        log(f"❌  Failed to save outputs: {e}")
        return False

    # Step 6: Move CV to processed_cv/
    log("📦  Step 5/5  → Moving file to processed_cv/ …")
    dest = PROCESSED_DIR / cv_path.name
    shutil.move(str(cv_path), str(dest))
    log(f"✅  Moved      : {dest}")

    elapsed = (datetime.now() - start).total_seconds()
    log(f"⏱️   Time taken : {elapsed:.1f}s")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    ensure_dirs()

    global_start = datetime.now()

    log_divider("═")
    log("🚀  CV PROCESSING STARTED")
    log(f"🕐  Start time  : {global_start.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"🤖  Model       : {MODEL}")
    log_divider("═")

    pdf_files = sorted(CV_DIR.glob("*.pdf"))
    total = len(pdf_files)

    if total == 0:
        log("⚠️   No PDF files found in cv/ directory. Exiting.")
        return

    log(f"📂  Found {total} CV(s) to process.\n")

    success_count = 0
    fail_count    = 0

    for idx, cv_path in enumerate(pdf_files, start=1):
        log_divider("─")
        ok = process_single_cv(cv_path, idx, total)
        if ok:
            success_count += 1
            log("🎉  Status     : SUCCESS")
        else:
            fail_count += 1
            log("💔  Status     : FAILED / SKIPPED")

    elapsed_total = (datetime.now() - global_start).total_seconds()
    minutes, seconds = divmod(int(elapsed_total), 60)

    log_divider("═")
    log("🏁  PROCESSING COMPLETE")
    log(f"📊  Total      : {total}")
    log(f"✅  Success    : {success_count}")
    log(f"❌  Failed     : {fail_count}")
    log(f"⏱️   Duration   : {minutes}m {seconds}s")
    log(f"📋  All data   : {ALL_CANDIDATES_FILE}")
    log_divider("═")


if __name__ == "__main__":
    main()