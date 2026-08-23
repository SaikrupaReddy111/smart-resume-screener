import json
import os
import re

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
USE_LLM = bool(GEMINI_API_KEY)

if USE_LLM:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    _model = genai.GenerativeModel(GEMINI_MODEL)


def extract_resume_data(resume_text: str) -> dict:
    if USE_LLM:
        return _extract_with_llm(resume_text)
    return _extract_with_heuristic(resume_text)


def score_match(resume_data: dict, job_description: str, resume_text: str) -> dict:
    if USE_LLM:
        return _score_with_llm(resume_data, job_description, resume_text)
    return _score_with_heuristic(resume_data, job_description)


EXTRACTION_PROMPT = """You are a resume parser. Read the resume text below and extract
structured information. Respond with ONLY valid JSON, no markdown fences, no commentary.

JSON shape:
{{
  "skills": ["skill1", "skill2", ...],
  "experience": "2-3 sentence summary of work experience (roles, years, companies)",
  "education": "1-2 sentence summary of degrees and institutions"
}}

Resume text:
---
{resume_text}
---
"""

MATCH_PROMPT = """Compare the following resume with this job description and rate fit on
1-10 with justification. Respond with ONLY valid JSON, no markdown fences, no commentary.

JSON shape:
{{
  "score": <number 1-10, can be decimal>,
  "justification": "2-4 sentences explaining the score, citing specific matching or
    missing skills/experience"
}}

Candidate skills: {skills}
Candidate experience: {experience}
Candidate education: {education}

Job description:
---
{job_description}
---
"""


def _call_gemini(prompt: str) -> dict:
    response = _model.generate_content(prompt)
    text = response.text.strip()
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def _extract_with_llm(resume_text: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(resume_text=resume_text[:8000])
    try:
        data = _call_gemini(prompt)
        return {
            "skills": data.get("skills", []),
            "experience": data.get("experience", ""),
            "education": data.get("education", ""),
        }
    except Exception as e:
        return _extract_with_heuristic(resume_text, error=str(e))


def _score_with_llm(resume_data: dict, job_description: str, resume_text: str) -> dict:
    prompt = MATCH_PROMPT.format(
        skills=", ".join(resume_data.get("skills", [])),
        experience=resume_data.get("experience", ""),
        education=resume_data.get("education", ""),
        job_description=job_description[:4000],
    )
    try:
        data = _call_gemini(prompt)
        return {"score": float(data.get("score", 0)), "justification": data.get("justification", "")}
    except Exception as e:
        return _score_with_heuristic(resume_data, job_description, error=str(e))


COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "react", "node.js", "sql",
    "aws", "docker", "kubernetes", "machine learning", "nlp", "fastapi",
    "django", "flask", "c++", "go", "git", "linux", "rest api", "graphql",
    "postgresql", "mongodb", "spring boot", "html", "css", "pandas", "numpy",
]


def _extract_with_heuristic(resume_text: str, error: str = None) -> dict:
    lower = resume_text.lower()
    found_skills = [s for s in COMMON_SKILLS if s in lower]
    return {
        "skills": found_skills,
        "experience": "Not extracted (no LLM configured) - see raw resume text.",
        "education": "Not extracted (no LLM configured) - see raw resume text.",
        "note": f"Fallback heuristic used. {error or ''}".strip(),
    }


def _score_with_heuristic(resume_data: dict, job_description: str, error: str = None) -> dict:
    jd_lower = job_description.lower()
    skills = resume_data.get("skills", [])
    matched = [s for s in skills if s.lower() in jd_lower]
    score = round(min(10, (len(matched) / max(1, len(skills))) * 10), 1) if skills else 0.0
    justification = (
        f"Heuristic match (no LLM configured): {len(matched)}/{len(skills)} extracted "
        f"skills appear in the job description ({', '.join(matched) or 'none'}). "
        f"Set GEMINI_API_KEY for real LLM-based scoring. {error or ''}"
    ).strip()
    return {"score": score, "justification": justification}
