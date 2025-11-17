import os
import platform
import subprocess
from pathlib import Path
import hashlib
import PyPDF2
try:
    from docx import Document
    HAVE_DOCX = True
except Exception as _e:
    Document = None
    HAVE_DOCX = False
    print("Aviso: python-docx no está disponible o es incompatible; las previews .docx estarán deshabilitadas.")

# Límites para previews/parsing que evitan DoS por archivos enormes
MAX_PREVIEW_CHARS = 300
MAX_PREVIEW_BYTES = 5 * 1024 * 1024  # 5 MB

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


def hash_file(path: Path, algorithms=('sha256', 'sha1', 'md5')) -> dict:
    """Calcular hashes en streaming para `path`.

    Devuelve un dict {alg: hexdigest}.
    """
    algos = {name: hashlib.new(name) for name in algorithms}
    try:
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                for h in algos.values():
                    h.update(chunk)
    except Exception as e:
        # En caso de error devolvemos lo que tengamos o un dict vacío
        print(f"Error calculando hash de {path}: {e}")
        return {}
    return {name: h.hexdigest() for name, h in algos.items()}


def hash_buffer(buf: bytes, algorithms=('sha256',)) -> dict:
    alg = algorithms[0]
    h = hashlib.new(alg)
    h.update(buf)
    return {alg: h.hexdigest()}


def get_file_preview(item: Path) -> str:
    try:
        ext = item.suffix.lower()
        size = item.stat().st_size if item.exists() else 0

        if ext in [".txt", ".csv", ".json", ".md", ".py", ".html", ".xml"]:
            # Leer solo los primeros MAX_PREVIEW_CHARS caracteres
            with open(item, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(MAX_PREVIEW_CHARS).replace("\n", " ").replace("\r", " ")

        elif ext == ".docx":
            # Si no tenemos python-docx instalado, devolvemos un mensaje claro
            if not HAVE_DOCX or Document is None:
                return "[python-docx no disponible: instalar python-docx para previews .docx]"
            # Evitar parsear DOCX enormes
            if size > MAX_PREVIEW_BYTES:
                return f"[DOCX demasiado grande para preview: {size} bytes]"
            try:
                doc = Document(item)
                text = " ".join(p.text for p in doc.paragraphs)
                return text[:MAX_PREVIEW_CHARS]
            except Exception as e:
                print(f"Error parseando DOCX {item}: {e}")
                return ""

        elif ext == ".pdf":
            # Evitar parsear PDFs enormes
            if size > MAX_PREVIEW_BYTES:
                return f"[PDF demasiado grande para preview: {size} bytes]"
            with open(item, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages[:3]:
                    try:
                        ptext = page.extract_text()
                    except Exception:
                        ptext = None
                    if ptext:
                        text += ptext
                return text[:MAX_PREVIEW_CHARS]

    except Exception as e:
        print(f"Error leyendo preview de {item}: {e}")
    return ""
