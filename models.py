"""
Pydantic models untuk API responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PDFMetadata(BaseModel):
    judul: Optional[str] = Field(None, description="Judul karya ilmiah")
    penulis: Optional[str] = Field(None, description="Nama penulis (dipisah koma jika lebih dari satu)")
    abstrak: Optional[str] = Field(None, description="Abstrak lengkap dari paper")
    kata_kunci: List[str] = Field([], description="Daftar kata kunci")
    file: str = Field(..., description="Nama file PDF")
    file_size: Optional[int] = Field(None, description="Ukuran file dalam bytes")
    extracted_at: Optional[str] = Field(None, description="Timestamp ekstraksi")
    

class PDFMetadataWithScore(PDFMetadata):
    relevance_score: int = Field(..., description="Skor relevansi untuk pencarian")


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
    results: List[PDFMetadataWithScore] = Field(..., description="Hasil pencarian")


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