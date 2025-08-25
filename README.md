# PDF Metadata Extractor API

API untuk ekstraksi metadata otomatis dari file PDF karya ilmiah.

## Cara Menjalankan

### 1. Clone Repository

```bash
git clone <repository-url>
cd pdf-extractor-api
```

### 2. Install Dependencies

```bash
# Buat virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# atau
venv\Scripts\activate     # Windows

# Install packages
pip install -r requirements.txt
```

### 3. Jalankan API

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

API akan berjalan di `http://localhost:8000`

## Fitur API

### 📄 Ekstraksi Metadata
- **GET `/extract`** - Ekstrak metadata dari semua PDF di folder BERKAS
- **GET `/extract/{filename}`** - Ekstrak metadata dari file PDF tertentu
- Metadata yang diekstrak: judul, penulis, abstrak, kata kunci

### 🔍 Pencarian
- **GET `/search?keyword=<keyword>`** - Cari PDF berdasarkan kata kunci
- Support parameter `limit` untuk membatasi hasil

### 📁 Manajemen File
- **GET `/list`** - Lihat daftar semua file PDF
- **POST `/upload`** - Upload file PDF baru
- **DELETE `/delete/{filename}`** - Hapus file PDF

### 📚 Dokumentasi Interaktif (Swagger)

API dilengkapi dengan dokumentasi interaktif yang memudahkan testing:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Cara Testing dengan Swagger:
1. Buka http://localhost:8000/docs di browser
2. Klik endpoint yang ingin ditest
3. Klik tombol **"Try it out"**
4. Isi parameter yang diperlukan
5. Klik **"Execute"** untuk menjalankan request
6. Lihat response di bagian bawah

**Fitur Swagger:**
- ✅ Testing langsung dari browser
- ✅ Contoh request dan response
- ✅ Dokumentasi parameter lengkap
- ✅ Schema model otomatis
- ✅ Download OpenAPI spec

### 🔗 Endpoints API
- **GET `/`** - Informasi API dan daftar endpoints

## Contoh Penggunaan

```bash
# Ekstrak metadata dari semua PDF
curl http://localhost:8000/extract

# Cari PDF dengan keyword
curl "http://localhost:8000/search?keyword=machine+learning"

# Upload PDF baru
curl -X POST "http://localhost:8000/upload" -F "file=@paper.pdf"

# Lihat daftar file
curl http://localhost:8000/list
```

## Struktur Project

```
pdf-extractor-api/
├── api.py          # Main API endpoints
├── models.py       # Pydantic response models  
├── extractors.py   # PDF extraction logic
├── config.py       # Configuration settings
├── requirements.txt # Dependencies
├── test_api.py     # Testing script
├── README.md       # Documentation
└── BERKAS/         # PDF storage folder
```

## Requirements

- Python 3.8+
- FastAPI
- PyPDF2  
- Uvicorn
- Pydantic

## Troubleshooting

### PDF tidak terbaca dengan baik
- Pastikan PDF tidak terproteksi/encrypted
- PDF harus mengandung teks (bukan scan gambar)
- Untuk PDF scan, perlu OCR terlebih dahulu