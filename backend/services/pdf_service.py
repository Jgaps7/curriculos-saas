import fitz, io

def read_pdf(path: str) -> str:
    text = ""
    with fitz.open(path) as pdf:
        for p in pdf:
            text += p.get_text()
    return text

def read_pdf_bytes(b: bytes) -> str:
    text = ""
    with fitz.open(stream=io.BytesIO(b), filetype="pdf") as pdf:
        for p in pdf:
            text += p.get_text()
    return text
