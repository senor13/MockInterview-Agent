import pdfplumber
import os

def parse_pdf (path : str) -> str:
    if not path:
        raise ValueError("Path cannot be empty")
    if os.path.exists(path):
        with pdfplumber.open(path) as pdf:
            pdf_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text is not None:
                    pdf_text += text
        return pdf_text  
    else:
        raise FileNotFoundError(f"path not found : {path}") 