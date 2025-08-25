from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict
import PyPDF2
import os
import re
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Metadata Extractor API",
    description="API untuk ekstraksi metadata dari file PDF karya ilmiah",
    version="1.0.0"
)

FOLDER = "BERKAS"

if not os.path.exists(FOLDER):
    os.makedirs(FOLDER)
    logger.info(f"Created directory: {FOLDER}")

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {str(e)}")
        return ""

def extract_metadata(text: str, filename: str = "") -> Dict:
    """Extract metadata from PDF text using regex and heuristics"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    metadata = {
        "judul": None,
        "penulis": None,
        "tahun": None,
        "abstrak": None,
        "kata_kunci": []
    }
    
    if lines:
        for i, line in enumerate(lines[:20]):
            if len(line) > 20 and len(line) < 200 and not any(x in line.lower() for x in ['universitas', 'fakultas', 'jurusan', 'program studi']):
                if not metadata["judul"]:
                    metadata["judul"] = line
                    break
    
    year_patterns = [
        r'\b(19|20)\d{2}\b',
        r'tahun\s*(19|20)\d{2}',
        r'©\s*(19|20)\d{2}'
    ]
    
    for pattern in year_patterns:
        year_match = re.search(pattern, text, re.IGNORECASE)
        if year_match:
            metadata["tahun"] = year_match.group(0).replace("tahun", "").replace("©", "").strip()
            break
    
    author_patterns = [
        r'(?:oleh|by|penulis|author)[\s:]*([^\n]+)',
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$'
    ]
    
    for pattern in author_patterns:
        for line in lines[:30]:
            author_match = re.search(pattern, line, re.IGNORECASE)
            if author_match:
                potential_author = author_match.group(1).strip()
                if len(potential_author) > 5 and len(potential_author) < 100:
                    metadata["penulis"] = potential_author
                    break
        if metadata["penulis"]:
            break
    
    abstract_start = None
    for i, line in enumerate(lines):
        if re.search(r'\b(abstrak|abstract)\b', line, re.IGNORECASE):
            abstract_start = i + 1
            break
    
    if abstract_start and abstract_start < len(lines):
        abstract_text = []
        for i in range(abstract_start, min(abstract_start + 20, len(lines))):
            if re.search(r'\b(kata kunci|keywords|pendahuluan|introduction)\b', lines[i], re.IGNORECASE):
                break
            abstract_text.append(lines[i])
        if abstract_text:
            metadata["abstrak"] = " ".join(abstract_text[:5])
    
    keyword_match = re.search(r'(?:kata kunci|keywords)[\s:]*([^\n]+)', text, re.IGNORECASE)
    if keyword_match:
        keywords = keyword_match.group(1).strip()
        metadata["kata_kunci"] = [k.strip() for k in re.split(r'[,;]', keywords) if k.strip()][:5]
    
    return metadata

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": "PDF Metadata Extractor API",
        "endpoints": {
            "/search": "Search PDFs by keyword",
            "/extract": "Extract metadata from all PDFs",
            "/extract/{filename}": "Extract metadata from specific PDF",
            "/upload": "Upload new PDF file",
            "/list": "List all PDF files"
        }
    }

@app.get("/search")
def search(
    keyword: str = Query(..., description="Kata kunci untuk pencarian dalam PDF"),
    limit: Optional[int] = Query(None, description="Limit jumlah hasil")
):
    """Search PDFs containing specific keyword"""
    if not os.path.exists(FOLDER):
        raise HTTPException(status_code=404, detail=f"Folder {FOLDER} tidak ditemukan")
    
    results = []
    files_checked = 0
    
    for filename in os.listdir(FOLDER):
        if filename.endswith(".pdf"):
            files_checked += 1
            path = os.path.join(FOLDER, filename)
            text = extract_text_from_pdf(path)
            
            if keyword.lower() in text.lower():
                meta = extract_metadata(text, filename)
                meta["file"] = filename
                meta["relevance_score"] = text.lower().count(keyword.lower())
                results.append(meta)
                
                if limit and len(results) >= limit:
                    break
    
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    return {
        "keyword": keyword,
        "total_files_checked": files_checked,
        "matches_found": len(results),
        "results": results
    }

@app.get("/extract")
def extract_all():
    """Extract metadata from all PDFs in BERKAS folder"""
    if not os.path.exists(FOLDER):
        raise HTTPException(status_code=404, detail=f"Folder {FOLDER} tidak ditemukan")
    
    results = []
    errors = []
    
    for filename in os.listdir(FOLDER):
        if filename.endswith(".pdf"):
            try:
                path = os.path.join(FOLDER, filename)
                text = extract_text_from_pdf(path)
                
                if text:
                    meta = extract_metadata(text, filename)
                    meta["file"] = filename
                    meta["file_size"] = os.path.getsize(path)
                    meta["extracted_at"] = datetime.now().isoformat()
                    results.append(meta)
                else:
                    errors.append({"file": filename, "error": "Could not extract text"})
                    
            except Exception as e:
                errors.append({"file": filename, "error": str(e)})
    
    return {
        "total_files": len(results) + len(errors),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None
    }

@app.get("/extract/{filename}")
def extract_single(filename: str):
    """Extract metadata from specific PDF file"""
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    path = os.path.join(FOLDER, filename)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File {filename} tidak ditemukan")
    
    try:
        text = extract_text_from_pdf(path)
        if not text:
            raise HTTPException(status_code=422, detail="Tidak dapat mengekstrak teks dari PDF")
        
        meta = extract_metadata(text, filename)
        meta["file"] = filename
        meta["file_size"] = os.path.getsize(path)
        meta["extracted_at"] = datetime.now().isoformat()
        
        return meta
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload new PDF file to BERKAS folder"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF")
    
    file_path = os.path.join(FOLDER, file.filename)
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        text = extract_text_from_pdf(file_path)
        meta = extract_metadata(text, file.filename)
        meta["file"] = file.filename
        meta["file_size"] = len(contents)
        meta["uploaded_at"] = datetime.now().isoformat()
        
        return {
            "message": f"File {file.filename} berhasil diupload",
            "metadata": meta
        }
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/list")
def list_files():
    """List all PDF files in BERKAS folder"""
    if not os.path.exists(FOLDER):
        raise HTTPException(status_code=404, detail=f"Folder {FOLDER} tidak ditemukan")
    
    files = []
    for filename in os.listdir(FOLDER):
        if filename.endswith(".pdf"):
            path = os.path.join(FOLDER, filename)
            files.append({
                "filename": filename,
                "size_bytes": os.path.getsize(path),
                "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            })
    
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    return {
        "total_files": len(files),
        "files": files
    }

@app.delete("/delete/{filename}")
def delete_file(filename: str):
    """Delete specific PDF file"""
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    path = os.path.join(FOLDER, filename)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File {filename} tidak ditemukan")
    
    try:
        os.remove(path)
        return {"message": f"File {filename} berhasil dihapus"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)