# CV Processor — Setup & Usage Guide

A local AI-powered tool that extracts structured data from PDF CVs using **Ollama** (runs entirely on your machine — no API keys, no cloud, no cost).

---

## What This Script Does

- Reads all PDF CVs from a `cv/` folder
- Extracts: name, email, career objective, skills, projects, work experience, education
- Saves results as individual JSON files + one combined `all_candidates.json`
- Appends skills, career objectives, and projects to separate text files for easy scanning
- Moves processed CVs to `processed_cv/` automatically
- Logs everything with timestamps

---

## Requirements

| Tool | Purpose |
|------|---------|
| Python 3.9+ | Run the script |
| Ollama | Local LLM runner |
| `mistral:latest` model | The AI brain (default) |
| `pdfplumber` | PDF text extraction (primary) |
| `PyMuPDF` | PDF text extraction (fallback) |
| `requests` | Talk to Ollama's API |

---

## Step 1 — Install Python

Check if you already have it:

```bash
python --version
# or
python3 --version
```

If not installed, download from [python.org](https://www.python.org/downloads/) and install. Make sure to check **"Add Python to PATH"** during installation (Windows).

---

## Step 2 — Install Ollama

Ollama lets you run AI models locally on your machine.

**Download:** [https://ollama.com/download](https://ollama.com/download)

Install it for your OS (Windows / macOS / Linux), then verify:

```bash
ollama --version
```

---

## Step 3 — Pull the AI Model

This script uses `mistral:latest` by default. Pull it once:

```bash
ollama pull mistral:latest
```

> This will download ~4GB. Run it once, it stays on your machine forever.

Want to use a different model? See the [Switching Models](#switching-models) section below.

---

## Step 4 — Start Ollama

Ollama needs to be running in the background before you run the script.

```bash
ollama serve
```

Leave this terminal open. Open a new terminal for the next steps.

> On Windows, Ollama may auto-start after installation. Check your system tray.

---

## Step 5 — Clone or Download the Project

If you have Git:

```bash
git clone <your-repo-url>
cd cv-processor
```

Or just download the ZIP and extract it, then open a terminal inside that folder.

---

## Step 6 — Install Python Dependencies

```bash
pip install pdfplumber pymupdf requests
```

Verify installation:

```bash
pip show pdfplumber
```

---

## Step 7 — Set Up the Folder Structure

Create these folders manually, or just run the script once and it will create them automatically:

```
your-project/
├── cv_processor.py       ← the main script
├── cv/                   ← PUT YOUR PDF CVs HERE
├── processed_cv/         ← processed CVs move here automatically
└── insights/             ← all output files land here
```

---

## Step 8 — Add Your CVs

Copy all your PDF CV files into the `cv/` folder.

```
cv/
├── john_doe_cv.pdf
├── jane_smith_cv.pdf
└── rafi_cv.pdf
```

> Only `.pdf` files are picked up. Word docs / images won't be processed.

---

## Step 9 — Run the Script

```bash
python cv_processor.py
```

You'll see live progress in the terminal like this:

```
═══════════════════════════════════════════════════════
[2025-01-15 10:23:01]  🚀  CV PROCESSING STARTED
[2025-01-15 10:23:01]  🤖  Model       : mistral:latest
═══════════════════════════════════════════════════════
[2025-01-15 10:23:01]  📂  Found 3 CV(s) to process.
───────────────────────────────────────────────────────
[2025-01-15 10:23:01]  📄  File       : john_doe_cv.pdf
[2025-01-15 10:23:01]  📊  Progress   : 1/3  |  Remaining after this: 2
[2025-01-15 10:23:01]  📝  Step 1/5  → Extracting text from PDF …
[2025-01-15 10:23:02]  🤖  Step 2/5  → Sending to Ollama …
[2025-01-15 10:23:18]  🔍  Step 3/5  → Parsing LLM response …
[2025-01-15 10:23:18]  ✅  Candidate  : John Doe  |  Email: john@email.com
[2025-01-15 10:23:18]  💾  Step 4/5  → Saving outputs …
[2025-01-15 10:23:18]  📦  Step 5/5  → Moving file to processed_cv/ …
[2025-01-15 10:23:18]  🎉  Status     : SUCCESS
```

---

## Output Files

After the script finishes, check the `insights/` folder:

| File | What's Inside |
|------|--------------|
| `all_candidates.json` | All candidates in one JSON array — best for searching/filtering |
| `skills.txt` | Unique skills collected across all CVs |
| `career_objective.txt` | Career objectives with candidate names |
| `projects.txt` | All projects grouped by candidate |
| `processlog.txt` | Full run log with timestamps |

Individual JSON files per candidate are saved in `processed_cv/`.

**Sample `all_candidates.json` entry:**

```json
[
  {
    "_source_file": "john_doe_cv.pdf",
    "full_name": "John Doe",
    "email": "john@example.com",
    "career_objective": "Seeking a challenging role in backend development...",
    "skills": ["Node.js", "MongoDB", "Docker", "REST APIs"],
    "projects": [
      {
        "name": "E-Commerce API",
        "details": "Built a scalable REST API using Node.js and MongoDB"
      }
    ],
    "work_experience": [
      {
        "company": "Tech Corp",
        "role": "Backend Developer",
        "duration": "2022–2024",
        "description": "Developed microservices..."
      }
    ],
    "education": [
      {
        "institution": "BUET",
        "degree": "BSc in CSE",
        "year": "2022"
      }
    ]
  }
]
```

---

## Switching Models

The default model is `mistral:latest`. To change it, open `cv_processor.py` and edit line ~30:

```python
MODEL = "mistral:latest"
# Change to any model you have pulled, for example:
# MODEL = "gemma2:9b"
# MODEL = "llama3.2:3b"
# MODEL = "qwen2.5:7b"
```

Pull any model first with `ollama pull <model-name>` before switching.

**Recommended models by hardware:**

| Your RAM | Recommended Model |
|----------|-------------------|
| 8GB | `llama3.2:3b` or `qwen2.5:3b` |
| 16GB | `mistral:latest` or `gemma2:9b` |
| 24GB+ | `gemma2:27b` or `llama3.1:8b` |

---

## Troubleshooting

**`Connection refused` / Ollama not responding**

Ollama is not running. Start it:
```bash
ollama serve
```

**`No PDF files found in cv/ directory`**

Make sure your PDFs are inside the `cv/` folder, not in a subfolder inside it.

**`❌ JSON parse error`**

The model gave a bad response. Try a different model or re-run. Some PDFs with complex formatting can confuse the parser on first try.

**`⚠️ Name is UNKNOWN`**

The AI couldn't find the candidate's name in the PDF. The file won't be moved. Check if the PDF is a scanned image (not text-based). Image-based PDFs need OCR — not supported in current version.

**Script is slow**

Normal — each CV takes 15–60 seconds depending on your hardware and model size. Larger models = slower but more accurate.

---

## Notes

- The script processes CVs **one at a time**, sequentially
- Already-processed CVs (moved to `processed_cv/`) won't be re-processed unless you move them back to `cv/`
- The `all_candidates.json` file **appends** on each run — it doesn't overwrite
- Maximum CV text sent to the model: **12,000 characters** per CV (configurable in code)

---
