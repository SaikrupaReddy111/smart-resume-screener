from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel

import database
import resume_parser
import llm_service

app = FastAPI(title="Smart Resume Screener API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()


class CandidateOut(BaseModel):
    id: int
    name: str
    resume_filename: str
    skills: List[str]
    experience: str
    education: str
    match_score: float
    justification: str

    class Config:
        from_attributes = True


def _to_out(c: database.Candidate) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "resume_filename": c.resume_filename,
        "skills": c.skills.split(",") if c.skills else [],
        "experience": c.experience,
        "education": c.education,
        "match_score": c.match_score,
        "justification": c.justification,
    }


@app.post("/api/screen")
async def screen_resume(
    name: str = Form(...),
    job_description: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(database.get_db),
):
    file_bytes = await resume.read()
    resume_text = resume_parser.extract_text_from_upload(resume.filename, file_bytes)

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the resume file.")

    extracted = llm_service.extract_resume_data(resume_text)
    match = llm_service.score_match(extracted, job_description, resume_text)

    candidate = database.Candidate(
        name=name,
        resume_filename=resume.filename,
        resume_text=resume_text,
        skills=",".join(extracted.get("skills", [])),
        experience=extracted.get("experience", ""),
        education=extracted.get("education", ""),
        job_description=job_description,
        match_score=match.get("score", 0.0),
        justification=match.get("justification", ""),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return _to_out(candidate)


@app.get("/api/candidates")
def list_candidates(db: Session = Depends(database.get_db)):
    candidates = db.query(database.Candidate).order_by(database.Candidate.match_score.desc()).all()
    return [_to_out(c) for c in candidates]


@app.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(database.get_db)):
    c = db.query(database.Candidate).filter(database.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    out = _to_out(c)
    out["resume_text"] = c.resume_text
    out["job_description"] = c.job_description
    return out


@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(database.get_db)):
    c = db.query(database.Candidate).filter(database.Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(c)
    db.commit()
    return {"deleted": candidate_id}


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": llm_service.USE_LLM}


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
