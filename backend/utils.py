import PyPDF2
from fastapi import UploadFile

def extract_text_from_pdf(file: UploadFile):
    pdf_reader = PyPDF2.PdfReader(file.file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text