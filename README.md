# Smart Resume Screener

Parses resumes, extracts structured candidate data, and scores fit against a job
description using an LLM - with a written justification for every score.

Built for the assignment brief: intelligently parse resumes, extract skills, and
match them with job descriptions.

## Live demo flow

1. Paste a job description and upload a candidate resume (PDF or .txt).
2. The backend extracts text from the resume, sends it to an LLM to pull out
   structured skills/experience/education, then asks the LLM to score the fit
   against the job description (1-10) with a written justification.
3. The dashboard lists all screened candidates sorted by match score, so the
   best-fit candidates float to the top.

## Architecture

Frontend (index.html, vanilla JS) sends a multipart form (name + resume file +
job description) to the FastAPI backend. The backend is split into three parts:

- resume_parser.py - turns the uploaded file into raw text. Has no opinion
  about what is "in" a resume, just bytes in, text out.
- llm_service.py - owns every prompt and is the only file that talks to the
  LLM. Two functions: extract_resume_data() and score_match(). Swapping LLM
  providers means editing only this file.
- database.py - a thin SQLAlchemy layer over SQLite. main.py never writes SQL
  directly.

main.py wires these together as FastAPI routes and returns JSON to the
frontend.

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy, SQLite
- LLM: Google Gemini API (gemini-2.5-flash) - chosen because it has a genuine
  free tier with no credit card required
- Frontend: single-page vanilla HTML/CSS/JS dashboard, no build step

## LLM prompts used

1. Structured extraction (resume_text -> skills/experience/education):

"You are a resume parser. Read the resume text below and extract structured
information. Respond with ONLY valid JSON... {"skills": [...], "experience":
"...", "education": "..."}"

2. Match scoring (candidate data + job description -> score + justification):

"Compare the following resume with this job description and rate fit on 1-10
with justification. Respond with ONLY valid JSON... {"score": <1-10>,
"justification": "..."}"

Full prompt templates live in backend/llm_service.py as EXTRACTION_PROMPT and
MATCH_PROMPT.

## Setup

1. Get a free Gemini API key at https://aistudio.google.com/apikey (no card
   required)
2. cd backend
3. python -m venv venv
4. venv\Scripts\Activate.ps1   (on Windows PowerShell)
5. pip install -r requirements.txt
6. Copy .env.example to .env and paste your GEMINI_API_KEY in
7. uvicorn main:app
8. Open http://127.0.0.1:8000

Without a Gemini key, the app still runs using a heuristic keyword-matching
fallback, so the full flow can be demoed with zero setup cost.

## API reference

- POST /api/screen - upload a resume + job description, get a score back
- GET /api/candidates - list all candidates, sorted by score descending
- GET /api/candidates/{id} - full detail for one candidate
- DELETE /api/candidates/{id} - remove a candidate
- GET /api/health - health check, reports whether LLM mode is active

## Project structure

resume_screener/
├── backend/
│ ├── main.py (FastAPI app and routes)
│ ├── database.py (SQLAlchemy models and session)
│ ├── resume_parser.py (PDF/text extraction)
│ ├── llm_service.py (LLM prompts, extraction and scoring logic)
│ ├── requirements.txt
│ └── .env.example
├── frontend/
│ └── index.html (Dashboard)
├── sample_data/
│ ├── sample_resume.txt
│ └── sample_job_description.txt
└── README.md

## Demo
https://drive.google.com/file/d/1TSqjN5blt-XHiuxNdXJGYpz68NslCnTP/view?usp=sharing

## Hosted URL
http://127.0.0.1:8000/
