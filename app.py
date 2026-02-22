from typing import List
from fastapi import FastAPI, UploadFile, HTTPException
from pathlib import Path
import tempfile
import os

from app_parser import detect_language, extract_structure
from doc_parser import parse_document

app = FastAPI()

CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".cs"}
DOC_EXTENSIONS  = {".pdf", ".docx", ".md", ".markdown", ".rst", ".txt"}

@app.post("/parse")
async def parse_files(files: List[UploadFile]):
    results = []

    for file in files:
        if not file.filename:
            continue

        ext = Path(file.filename).suffix.lower()
        raw = await file.read()

        if ext in CODE_EXTENSIONS:
            try:
                code = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                results.append({
                    
                    "error": "File is not valid UTF-8."
                })
                continue

            language = detect_language(file.filename, code)
            results.append({
                
                "structure": extract_structure(language, code, file.filename)
            })

        elif ext in DOC_EXTENSIONS:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            try:
                result = parse_document(tmp_path)
                results.append({ "structure": result})
            finally:
                os.unlink(tmp_path)

        else:
            results.append({
                
                "error": f"Unsupported file type: {ext}"
            })

    return results

