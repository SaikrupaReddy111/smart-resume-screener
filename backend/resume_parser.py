import io
from pypdf import PdfReader


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return _extract_text_from_pdf(file_bytes)
    return file_bytes.decode("utf-8", errors="ignore")


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text).strip()
