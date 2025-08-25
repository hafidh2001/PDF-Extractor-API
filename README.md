# PDF Metadata Extractor API

API untuk membaca dan mengekstrak metadata dari file PDF karya ilmiah yang berjalan secara lokal (on-premise).

## Fitur

- 📄 **Ekstraksi Metadata Otomatis**: Mengekstrak judul, penulis, tahun terbit, abstrak, dan kata kunci dari PDF
- 🔍 **Pencarian Berdasarkan Keyword**: Mencari PDF yang mengandung kata kunci tertentu
- 📁 **Manajemen File**: Upload, list, dan hapus file PDF
- 🚀 **REST API**: Akses melalui HTTP request
- 💾 **On-Premise**: Berjalan 100% di lokal tanpa cloud

## Persyaratan Sistem

- Python 3.8 atau lebih tinggi
- pip (Python package manager)

## Instalasi

### 1. Clone atau Download Project

```bash
cd pdf-extractor-api
```

### 2. Buat Virtual Environment (Opsional tapi Disarankan)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Buat Folder BERKAS

Folder ini akan otomatis dibuat saat API pertama kali dijalankan, atau buat manual:

```bash
mkdir BERKAS
```

## Cara Menjalankan

### Metode 1: Menggunakan Uvicorn (Recommended)

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Metode 2: Menjalankan Script Langsung

```bash
python api.py
```

API akan berjalan di `http://localhost:8000`

## Dokumentasi API

### Endpoints Tersedia

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/` | Informasi API dan daftar endpoints |
| GET | `/search` | Cari PDF berdasarkan keyword |
| GET | `/extract` | Ekstrak metadata dari semua PDF |
| GET | `/extract/{filename}` | Ekstrak metadata dari PDF tertentu |
| POST | `/upload` | Upload file PDF baru |
| GET | `/list` | Lihat daftar semua file PDF |
| DELETE | `/delete/{filename}` | Hapus file PDF |

### Contoh Penggunaan

#### 1. Cari PDF dengan Keyword

```bash
# Menggunakan curl
curl "http://localhost:8000/search?keyword=blockchain"

# Menggunakan browser
http://localhost:8000/search?keyword=blockchain

# Dengan limit hasil
http://localhost:8000/search?keyword=blockchain&limit=5
```

Response:
```json
{
  "keyword": "blockchain",
  "total_files_checked": 10,
  "matches_found": 3,
  "results": [
    {
      "judul": "Implementasi Blockchain untuk Sistem Keuangan",
      "penulis": "Ahmad Fauzan",
      "tahun": "2022",
      "abstrak": "Penelitian ini membahas...",
      "kata_kunci": ["blockchain", "fintech", "security"],
      "file": "blockchain_jurnal.pdf",
      "relevance_score": 15
    }
  ]
}
```

#### 2. Ekstrak Metadata dari Semua PDF

```bash
curl http://localhost:8000/extract
```

Response:
```json
{
  "total_files": 5,
  "successful": 5,
  "failed": 0,
  "results": [
    {
      "judul": "Pengaruh AI terhadap Pendidikan",
      "penulis": "Budi Santoso",
      "tahun": "2023",
      "abstrak": "Artificial Intelligence telah...",
      "kata_kunci": ["AI", "education", "machine learning"],
      "file": "ai_education.pdf",
      "file_size": 2548965,
      "extracted_at": "2024-01-20T10:30:00"
    }
  ],
  "errors": null
}
```

#### 3. Upload PDF Baru

```bash
# Menggunakan curl
curl -X POST "http://localhost:8000/upload" \
  -F "file=@/path/to/your/document.pdf"

# Menggunakan Python
import requests

with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/upload", files=files)
    print(response.json())
```

#### 4. Lihat Daftar File PDF

```bash
curl http://localhost:8000/list
```

Response:
```json
{
  "total_files": 3,
  "files": [
    {
      "filename": "jurnal1.pdf",
      "size_bytes": 1548965,
      "size_mb": 1.48,
      "modified": "2024-01-20T09:15:00"
    }
  ]
}
```

#### 5. Hapus File PDF

```bash
curl -X DELETE http://localhost:8000/delete/jurnal1.pdf
```

## Akses Interactive API Documentation

FastAPI menyediakan dokumentasi interaktif otomatis:

1. **Swagger UI**: http://localhost:8000/docs
2. **ReDoc**: http://localhost:8000/redoc

Di sini Anda bisa mencoba semua endpoint langsung dari browser.

## Struktur Project

```
pdf-extractor-api/
│
├── api.py              # Script utama API
├── requirements.txt    # Daftar dependencies
├── README.md          # Dokumentasi ini
├── test_api.py        # Script untuk testing
├── .gitignore         # File yang diabaikan git
└── BERKAS/            # Folder penyimpanan PDF
    ├── jurnal1.pdf
    ├── jurnal2.pdf
    └── ...
```

## Testing API

Jalankan script test untuk memverifikasi semua endpoint:

```bash
python test_api.py
```

## Cara Kerja Ekstraksi Metadata

API menggunakan kombinasi teknik:

1. **Ekstraksi Teks**: Menggunakan PyMuPDF untuk membaca konten PDF
2. **Pattern Matching**: Regex untuk mencari pola seperti tahun (19xx/20xx)
3. **Heuristik**: Logika untuk menentukan judul (biasanya di awal dokumen)
4. **Keyword Detection**: Mencari kata kunci seperti "oleh", "author", "abstrak", dll

## Troubleshooting

### Error: "Module not found"
```bash
pip install -r requirements.txt
```

### Error: "Port 8000 already in use"
```bash
# Ganti port
uvicorn api:app --reload --port 8001
```

### PDF tidak terbaca dengan baik
- Pastikan PDF tidak terproteksi/encrypted
- PDF harus mengandung teks (bukan scan gambar)
- Untuk PDF scan, perlu OCR terlebih dahulu

## Pengembangan Lanjutan

### Menambah Field Metadata Baru

Edit fungsi `extract_metadata()` di `api.py`:

```python
metadata = {
    "judul": None,
    "penulis": None,
    "tahun": None,
    "abstrak": None,
    "kata_kunci": [],
    "universitas": None,  # Field baru
    "pembimbing": None    # Field baru
}
```

### Integrasi dengan Database

Untuk production, bisa tambahkan database:

```python
# Contoh dengan SQLite
import sqlite3

def save_to_database(metadata):
    conn = sqlite3.connect('metadata.db')
    # ... implementasi database
```

### Meningkatkan Akurasi dengan AI/NLP

Bisa integrasikan model NLP untuk ekstraksi lebih akurat:

```python
# Contoh dengan spaCy atau Hugging Face
from transformers import pipeline

ner = pipeline("ner", model="indobenchmark/indobert-base-p1")
```

## Keamanan

Untuk production environment:

1. Tambahkan autentikasi (API key, JWT)
2. Batasi ukuran file upload
3. Validasi tipe file
4. Setup HTTPS
5. Rate limiting

## Lisensi

MIT License - Bebas digunakan dan dimodifikasi

## Kontribusi

Pull requests are welcome! Untuk perubahan besar, silakan buka issue terlebih dahulu.

## Support

Jika ada pertanyaan atau masalah, silakan buka issue di repository ini.