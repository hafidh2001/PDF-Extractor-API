from fastapi import FastAPI, Query, HTTPException, UploadFile, File, status, Path
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
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
    description="""
    ## 📚 API untuk ekstraksi metadata otomatis dari file PDF karya ilmiah
    
    ### Fitur Utama:
    - 🔍 **Ekstraksi Metadata**: Ekstrak judul, penulis, abstrak, dan kata kunci dari PDF
    - 📂 **Manajemen File**: Upload, list, dan hapus file PDF
    - 🔎 **Pencarian**: Cari PDF berdasarkan keyword
    
    ### Cara Penggunaan:
    1. Upload file PDF menggunakan endpoint `/upload`
    2. Gunakan `/extract` untuk mengekstrak metadata dari semua PDF
    3. Atau gunakan `/search` untuk mencari PDF berdasarkan keyword
    
    ### Testing:
    Klik tombol **Try it out** pada setiap endpoint untuk menguji langsung dari browser ini.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Pydantic models untuk response
class PDFMetadata(BaseModel):
    judul: Optional[str] = Field(None, description="Judul karya ilmiah")
    penulis: Optional[str] = Field(None, description="Nama penulis (dipisah koma jika lebih dari satu)")
    abstrak: Optional[str] = Field(None, description="Abstrak lengkap dari paper")
    kata_kunci: List[str] = Field([], description="Daftar kata kunci")
    file: str = Field(..., description="Nama file PDF")
    file_size: Optional[int] = Field(None, description="Ukuran file dalam bytes")
    extracted_at: Optional[str] = Field(None, description="Timestamp ekstraksi")
    relevance_score: Optional[int] = Field(None, description="Skor relevansi untuk pencarian")

class ExtractAllResponse(BaseModel):
    total_files: int = Field(..., description="Total file yang diproses")
    successful: int = Field(..., description="Jumlah file berhasil diekstrak")
    failed: int = Field(..., description="Jumlah file gagal diekstrak")
    results: List[PDFMetadata] = Field(..., description="Hasil ekstraksi metadata")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Daftar error jika ada")

class SearchResponse(BaseModel):
    keyword: str = Field(..., description="Kata kunci pencarian")
    total_files_checked: int = Field(..., description="Total file yang diperiksa")
    matches_found: int = Field(..., description="Jumlah file yang cocok")
    results: List[PDFMetadata] = Field(..., description="Hasil pencarian")

class FileInfo(BaseModel):
    filename: str = Field(..., description="Nama file")
    size_bytes: int = Field(..., description="Ukuran dalam bytes")
    size_mb: float = Field(..., description="Ukuran dalam MB")
    modified: str = Field(..., description="Tanggal terakhir dimodifikasi")

class ListFilesResponse(BaseModel):
    total_files: int = Field(..., description="Total file PDF")
    files: List[FileInfo] = Field(..., description="Daftar file")

class MessageResponse(BaseModel):
    message: str = Field(..., description="Pesan response")

class UploadResponse(BaseModel):
    message: str = Field(..., description="Pesan upload")
    metadata: PDFMetadata = Field(..., description="Metadata file yang diupload")

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
    """Extract metadata from PDF text using improved regex and heuristics"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    metadata = {
        "judul": None,
        "penulis": None,
        "abstrak": None,
        "kata_kunci": []
    }
    
    # Clean lines from page numbers and headers
    cleaned_lines = []
    for line in lines:
        # Skip page numbers, headers, footers
        if re.match(r'^[\d\s]+$', line):  # Only numbers
            continue
        if re.match(r'^Page\s+\d+', line, re.IGNORECASE):
            continue
        # Skip very short lines (1-2 chars)
        if len(line) <= 2:
            continue
        cleaned_lines.append(line)
    
    lines = cleaned_lines
    
    # Extract Title and Authors together
    # Look for patterns where title ends and authors begin
    title_lines = []
    author_lines = []
    found_authors = False
    
    skip_words = ['universitas', 'fakultas', 'jurusan', 'program studi', 'issn', 'vol.', 'volume', 'jurnal', 'email', '@', 'doi:', 'http://', 'https://']
    
    for i, line in enumerate(lines[:50]):  # Increased range to catch more title lines
        # Skip institutional headers and URLs
        if any(word in line.lower() for word in skip_words):
            continue
        
        # Skip lines that are clearly page numbers or headers
        if len(line) < 5 or line.isdigit():
            continue
            
        # Check if this looks like an author line - names with numbers and commas
        # Pattern like: "Name Name1, Name2" or "Name1, Name2"
        if re.search(r'[A-Z][a-z]+\s*\d+\s*,\s*[A-Z][a-z]+', line):
            # Confirm it's not part of the abstract (check for narrative words)
            if not any(word in line.lower() for word in ['pada', 'tahun', 'oleh', 'dengan', 'yang', 'abstrak']):
                # This is definitely an author line
                author_lines.append(line)
                found_authors = True
                # Check next few lines for affiliations only
                for j in range(1, 3):
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        # Stop at abstract
                        if 'abstrak' in next_line.lower() or 'abstract' in next_line.lower():
                            break
                        # Add affiliations
                        if any(x in next_line.lower() for x in ['universitas', 'fakultas', 'manajemen', '@']):
                            author_lines.append(next_line)
                        else:
                            break
                continue
        
        # Collect title lines if we haven't found authors yet
        if not found_authors:
            # Skip if line is just a single number (page number)
            if re.match(r'^\d{1,3}$', line):
                continue
            # Skip if line looks like date/year only
            if re.match(r'^\d{4}$', line) or re.match(r'^[A-Z][a-z]+\s+\d{4}$', line):
                continue
            # This is likely part of the title
            title_lines.append(line)
            
        elif found_authors:
            # Stop collecting once we're past authors
            break
    
    # Process title - join all title lines
    if title_lines:
        # Join title lines with space
        title_text = " ".join(title_lines)
        # Clean up extra spaces and normalize
        title_text = re.sub(r'\s+', ' ', title_text).strip()
        # Remove any trailing author patterns that might have slipped in
        title_text = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]+$', '', title_text).strip()
        if title_text:
            metadata["judul"] = title_text
    
    # Process authors
    if author_lines:
        authors = []
        for line in author_lines:
            # Skip pure affiliation lines (start with D4, S1, etc. or contain universitas)
            if re.match(r'^(D4|S1|S2|S3|Manajemen|Fakultas)', line) or 'universitas' in line.lower():
                continue
            # Skip email lines
            if '@' in line:
                continue
            # Remove superscript numbers and clean
            clean_line = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]+', '', line)
            clean_line = re.sub(r'\d+', '', clean_line)
            # Split by comma and extract names
            parts = clean_line.split(',')
            for part in parts:
                part = part.strip()
                # Check if it looks like a name (Title Case with at least 2 words)
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', part) and len(part.split()) >= 2:
                    authors.append(part)
        
        if authors:
            # Remove duplicates while preserving order
            seen = set()
            unique_authors = []
            for author in authors:
                if author not in seen:
                    seen.add(author)
                    unique_authors.append(author)
            metadata["penulis"] = ", ".join(unique_authors[:10])  # Allow up to 10 authors
    
    # If no authors found with pattern, try alternative approach
    if not metadata["penulis"] and metadata["judul"]:
        # Look for lines immediately after title
        title_found_at = -1
        for i, line in enumerate(lines[:60]):
            # Find where the title ends
            if metadata["judul"][:50] in line or line in metadata["judul"]:
                title_found_at = i
                # Check next 5 lines for authors
                for j in range(1, 6):
                    if i + j < len(lines):
                        check_line = lines[i + j]
                        # Skip empty or very short lines
                        if len(check_line) < 5:
                            continue
                        # Stop at abstract
                        if any(x in check_line.lower() for x in ['abstrak', 'abstract']):
                            break
                        # Look for name patterns
                        if re.match(r'^[A-Z][a-z]+', check_line) and '@' not in check_line:
                            # Extract all names from the line
                            names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', check_line)
                            if names:
                                # Filter out single words (likely not names)
                                names = [n for n in names if ' ' in n]
                                if names:
                                    metadata["penulis"] = ", ".join(names[:10])
                                    break
                break
    
    # Extract Abstract
    abstract_text = []
    abstract_start = None
    
    # Look for abstract keyword
    for i, line in enumerate(lines):
        # Check for standalone abstract header
        if re.match(r'^(abstrak|abstract)\s*[-—:]?\s*$', line, re.IGNORECASE):
            abstract_start = i + 1
            break
        # Check for abstract with dash or em-dash followed by content
        elif re.match(r'^(abstrak|abstract)\s*[-—]', line, re.IGNORECASE):
            # Extract content after the dash
            abstract_content = re.sub(r'^(abstrak|abstract)\s*[-—]\s*', '', line, flags=re.IGNORECASE)
            if abstract_content:
                abstract_text.append(abstract_content)
            abstract_start = i + 1
            break
    
    if abstract_start and abstract_start < len(lines):
        # Collect abstract lines until we hit keywords or next section
        for i in range(abstract_start, min(abstract_start + 100, len(lines))):  # Increased range
            if i < len(lines):
                line = lines[i]
                # Stop conditions - check for section headers or keywords
                if re.match(r'^(kata kunci|keywords?)\s*[-—:]', line, re.IGNORECASE):
                    break
                if re.match(r'^(pendahuluan|introduction|latar belakang|^I\.\s|^1\.\s)', line, re.IGNORECASE):
                    break
                # Skip very short lines unless they're part of a sentence
                if len(line) > 5:
                    abstract_text.append(line)
    
    if abstract_text:
        # Join and clean the abstract
        full_abstract = " ".join(abstract_text)
        # Remove extra spaces
        full_abstract = re.sub(r'\s+', ' ', full_abstract).strip()
        metadata["abstrak"] = full_abstract
    
    # Extract Keywords
    keywords_section = ""
    for i, line in enumerate(lines):
        # Look for keywords header with various formats
        if re.search(r'(kata[\s\-]?kunci|key[\s\-]?words?)\s*[-—:.)]', line, re.IGNORECASE):
            # Make sure it's not part of the abstract text
            if not any(word in line.lower() for word in ['pada', 'tahun', 'dengan', 'yang', 'untuk']):
                # Extract keywords from the same line if present
                keywords_section = re.sub(r'^.*(kata[\s\-]?kunci|key[\s\-]?words?)\s*[-—:.]\s*', '', line, flags=re.IGNORECASE)
                # Check next 2 lines for continuation
                for j in range(1, 3):
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        # Stop if we hit a new section
                        if re.match(r'^(abstract|abstrak|pendahuluan|introduction|latar belakang|^I\.\s|^1\.\s)', next_line, re.IGNORECASE):
                            break
                        # Add if it looks like keywords (not a full sentence)
                        if len(next_line) < 150 and '.' not in next_line[-1:] and not any(w in next_line.lower() for w in ['pada', 'tahun', 'dengan']):
                            keywords_section += " " + next_line
                break
    
    if keywords_section:
        # Clean and normalize separators
        keywords_section = keywords_section.replace(";", ",")
        keywords_section = keywords_section.replace(" dan ", ", ")
        keywords_section = keywords_section.replace(" and ", ", ")
        
        # Split by comma and clean
        keywords = []
        for k in keywords_section.split(','):
            k = k.strip()
            # Remove trailing dots
            k = k.rstrip('.')
            # Only keep valid keywords
            if k and len(k) > 2 and len(k) < 100:
                keywords.append(k)
        
        if keywords:
            metadata["kata_kunci"] = keywords[:15]  # Allow up to 15 keywords
    
    return metadata

@app.get("/", 
    tags=["Info"],
    summary="API Information",
    description="Mendapatkan informasi tentang API dan daftar endpoint yang tersedia",
    response_description="Informasi API dan endpoints")
def root():
    """
    Root endpoint untuk mendapatkan informasi API.
    
    Gunakan endpoint ini untuk:
    - Memeriksa apakah API berjalan
    - Melihat daftar endpoint yang tersedia
    
    **Contoh Response:**
    ```json
    {
        "message": "PDF Metadata Extractor API",
        "endpoints": {...}
    }
    ```
    """
    return {
        "message": "PDF Metadata Extractor API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/search": "Search PDFs by keyword",
            "/extract": "Extract metadata from all PDFs",
            "/extract/{filename}": "Extract metadata from specific PDF",
            "/upload": "Upload new PDF file",
            "/list": "List all PDF files",
            "/delete/{filename}": "Delete specific PDF"
        }
    }

@app.get("/search",
    tags=["Search"],
    summary="Cari PDF berdasarkan keyword",
    description="Mencari file PDF yang mengandung kata kunci tertentu dalam kontennya",
    response_model=SearchResponse,
    responses={
        200: {
            "description": "Pencarian berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "keyword": "machine learning",
                        "total_files_checked": 5,
                        "matches_found": 2,
                        "results": [
                            {
                                "judul": "Implementasi Machine Learning untuk Deteksi Objek",
                                "penulis": "Ahmad Fauzi, Budi Santoso",
                                "abstrak": "Penelitian ini membahas...",
                                "kata_kunci": ["machine learning", "object detection"],
                                "file": "ml_paper.pdf",
                                "relevance_score": 15
                            }
                        ]
                    }
                }
            }
        },
        404: {"description": "Folder BERKAS tidak ditemukan"}
    })
def search(
    keyword: str = Query(
        ..., 
        description="Kata kunci untuk pencarian dalam PDF",
        example="machine learning",
        min_length=1
    ),
    limit: Optional[int] = Query(
        None, 
        description="Limit jumlah hasil yang dikembalikan",
        example=10,
        ge=1,
        le=100
    )
) -> SearchResponse:
    """
    Mencari PDF yang mengandung keyword tertentu.
    
    ### Cara Penggunaan:
    1. Masukkan keyword yang ingin dicari
    2. Opsional: Set limit untuk membatasi hasil
    3. API akan mencari keyword di seluruh konten PDF
    
    ### Catatan:
    - Pencarian bersifat case-insensitive
    - Hasil diurutkan berdasarkan relevance score (frekuensi keyword)
    - Jika limit tidak diset, semua hasil akan dikembalikan
    """
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

@app.get("/extract",
    tags=["Extract"],
    summary="Ekstrak metadata dari semua PDF",
    description="Mengekstrak metadata (judul, penulis, abstrak, kata kunci) dari semua file PDF dalam folder BERKAS",
    response_model=ExtractAllResponse,
    responses={
        200: {
            "description": "Ekstraksi berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "total_files": 3,
                        "successful": 3,
                        "failed": 0,
                        "results": [
                            {
                                "judul": "Sistem Pendeteksian Wajah Menggunakan CNN",
                                "penulis": "Muhammad Rizki, Siti Aminah",
                                "abstrak": "Penelitian ini mengembangkan sistem...",
                                "kata_kunci": ["face detection", "CNN", "deep learning"],
                                "file": "face_detection.pdf",
                                "file_size": 2548965,
                                "extracted_at": "2024-01-20T10:30:00"
                            }
                        ],
                        "errors": None
                    }
                }
            }
        },
        404: {"description": "Folder BERKAS tidak ditemukan"}
    })
def extract_all() -> ExtractAllResponse:
    """
    Ekstrak metadata dari semua PDF dalam folder BERKAS.
    
    ### Metadata yang diekstrak:
    - **Judul**: Judul lengkap karya ilmiah (multi-line supported)
    - **Penulis**: Nama-nama penulis
    - **Abstrak**: Abstrak lengkap dari paper
    - **Kata Kunci**: Keywords dari paper
    
    ### Catatan:
    - Proses mungkin memakan waktu untuk banyak file
    - File yang gagal diekstrak akan masuk ke array errors
    - Ekstraksi menggunakan pattern recognition untuk paper Indonesia
    """
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

@app.get("/extract/{filename}",
    tags=["Extract"],
    summary="Ekstrak metadata dari PDF tertentu",
    description="Mengekstrak metadata dari file PDF spesifik berdasarkan nama file",
    response_model=PDFMetadata,
    responses={
        200: {
            "description": "Ekstraksi berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "judul": "Implementasi IoT untuk Smart Home",
                        "penulis": "Andi Wijaya",
                        "abstrak": "Smart home merupakan konsep...",
                        "kata_kunci": ["IoT", "smart home", "automation"],
                        "file": "iot_paper.pdf",
                        "file_size": 1548965,
                        "extracted_at": "2024-01-20T10:30:00"
                    }
                }
            }
        },
        404: {"description": "File tidak ditemukan"},
        422: {"description": "Tidak dapat mengekstrak teks dari PDF"},
        500: {"description": "Error saat memproses file"}
    })
def extract_single(
    filename: str = Path(
        ...,
        description="Nama file PDF (dengan atau tanpa ekstensi .pdf)",
        example="paper.pdf"
    )
) -> PDFMetadata:
    """
    Ekstrak metadata dari file PDF tertentu.
    
    ### Cara Penggunaan:
    1. Masukkan nama file PDF (contoh: 'paper.pdf' atau 'paper')
    2. API akan mengekstrak metadata dari file tersebut
    
    ### Catatan:
    - Ekstensi .pdf akan ditambahkan otomatis jika tidak ada
    - File harus ada dalam folder BERKAS
    - Pastikan PDF mengandung teks (bukan scan)
    """
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

@app.post("/upload",
    tags=["File Management"],
    summary="Upload file PDF baru",
    description="Upload file PDF ke folder BERKAS dan ekstrak metadata-nya secara otomatis",
    response_model=UploadResponse,
    responses={
        200: {
            "description": "Upload berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "message": "File paper.pdf berhasil diupload",
                        "metadata": {
                            "judul": "Analisis Sentimen Media Sosial",
                            "penulis": "Dewi Sartika",
                            "abstrak": "Analisis sentimen adalah...",
                            "kata_kunci": ["sentiment analysis", "NLP"],
                            "file": "paper.pdf",
                            "file_size": 2048576,
                            "uploaded_at": "2024-01-20T10:30:00"
                        }
                    }
                }
            }
        },
        400: {"description": "File harus berformat PDF"},
        500: {"description": "Error saat upload file"}
    })
async def upload_pdf(
    file: UploadFile = File(
        ...,
        description="File PDF yang akan diupload"
    )
) -> UploadResponse:
    """
    Upload file PDF baru ke sistem.
    
    ### Cara Penggunaan:
    1. Klik tombol 'Try it out'
    2. Klik 'Choose File' dan pilih file PDF
    3. Klik 'Execute' untuk upload
    
    ### Catatan:
    - Hanya menerima file dengan ekstensi .pdf
    - File akan disimpan di folder BERKAS
    - Metadata akan diekstrak otomatis setelah upload
    - Ukuran file maksimal tergantung konfigurasi server
    """
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

@app.get("/list",
    tags=["File Management"],
    summary="Lihat daftar semua file PDF",
    description="Menampilkan daftar semua file PDF yang ada dalam folder BERKAS beserta informasinya",
    response_model=ListFilesResponse,
    responses={
        200: {
            "description": "Daftar file berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "total_files": 3,
                        "files": [
                            {
                                "filename": "paper1.pdf",
                                "size_bytes": 2548965,
                                "size_mb": 2.43,
                                "modified": "2024-01-20T09:15:00"
                            },
                            {
                                "filename": "paper2.pdf",
                                "size_bytes": 1548965,
                                "size_mb": 1.48,
                                "modified": "2024-01-19T14:30:00"
                            }
                        ]
                    }
                }
            }
        },
        404: {"description": "Folder BERKAS tidak ditemukan"}
    })
def list_files() -> ListFilesResponse:
    """
    Menampilkan daftar semua file PDF.
    
    ### Informasi yang ditampilkan:
    - Nama file
    - Ukuran file (bytes dan MB)
    - Tanggal terakhir dimodifikasi
    
    ### Catatan:
    - File diurutkan berdasarkan tanggal modifikasi (terbaru dulu)
    - Hanya menampilkan file dengan ekstensi .pdf
    """
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

@app.delete("/delete/{filename}",
    tags=["File Management"],
    summary="Hapus file PDF",
    description="Menghapus file PDF tertentu dari folder BERKAS",
    response_model=MessageResponse,
    responses={
        200: {
            "description": "File berhasil dihapus",
            "content": {
                "application/json": {
                    "example": {
                        "message": "File paper.pdf berhasil dihapus"
                    }
                }
            }
        },
        404: {"description": "File tidak ditemukan"},
        500: {"description": "Error saat menghapus file"}
    })
def delete_file(
    filename: str = Path(
        ...,
        description="Nama file PDF yang akan dihapus",
        example="paper.pdf"
    )
) -> MessageResponse:
    """
    Hapus file PDF dari sistem.
    
    ### Cara Penggunaan:
    1. Masukkan nama file yang ingin dihapus
    2. File akan dihapus permanen dari folder BERKAS
    
    ### Peringatan:
    - Operasi ini tidak dapat dibatalkan
    - File akan dihapus permanen
    - Pastikan nama file benar sebelum menghapus
    """
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