"""
Main API endpoints for PDF Metadata Extractor
"""
from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Path
from typing import Optional
import os
from datetime import datetime

# Import dari module terpisah
from models import (
    PDFMetadata, PDFMetadataWithScore, ExtractAllResponse, SearchResponse,
    FileInfo, ListFilesResponse, MessageResponse, UploadResponse
)
from extractors import extract_text_from_pdf, extract_metadata
from config import (
    FOLDER, logger, API_TITLE, API_DESCRIPTION, API_VERSION, 
    API_CONTACT, API_LICENSE
)

# Inisialisasi FastAPI dengan konfigurasi dari config.py
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    contact=API_CONTACT,
    license_info=API_LICENSE
)


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