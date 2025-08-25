"""
Configuration settings for the API
"""
import os
import logging

# Folder untuk menyimpan file PDF
FOLDER = "BERKAS"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Buat folder jika belum ada
if not os.path.exists(FOLDER):
    os.makedirs(FOLDER)
    logger.info(f"Created directory: {FOLDER}")

# API Configuration
API_TITLE = "PDF Metadata Extractor API"
API_DESCRIPTION = """
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
"""
API_VERSION = "1.0.0"
API_CONTACT = {
    "name": "API Support",
    "email": "support@example.com"
}
API_LICENSE = {
    "name": "MIT License",
    "url": "https://opensource.org/licenses/MIT"
}