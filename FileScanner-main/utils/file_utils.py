import os
import platform
import subprocess
from pathlib import Path
import PyPDF2
from docx import Document

def open_folder(path: str):
    try:
        if os.path.isdir(path):
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        elif os.path.isfile(path):
            folder = os.path.dirname(path)
            if platform.system() == "Windows":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
    except Exception as e:
        print(f"Error abriendo carpeta: {e}")

def get_file_preview(item: Path) -> str:
    try:
        ext = item.suffix.lower()
        if ext in [".txt", ".csv", ".json", ".md", ".py", ".html", ".xml"]:
            with open(item, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(300).replace("\n", " ").replace("\r", " ")
        elif ext == ".docx":
            doc = Document(item)
            text = " ".join(p.text for p in doc.paragraphs)
            return text[:300]
        elif ext == ".pdf":
            with open(item, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages[:3]:
                    if page.extract_text():
                        text += page.extract_text()
                return text[:300]
    except Exception as e:
        print(f"Error leyendo preview de {item}: {e}")
    return ""
