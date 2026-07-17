Item List Revision
===================

Deskripsi
---------
Sebuah aplikasi web sederhana berbasis Flask untuk menampilkan, mengedit, dan mengelola daftar item. Termasuk layanan impor/ekspor Excel dan utilitas pengembangan lokal.

Prasyarat
---------
- Python 3.8 atau lebih baru
- pip

Instalasi
---------
1. Buka terminal pada folder project:

   cd c:\Users\manur\OneDrive\Documents\item-list-revision

2. Pasang dependensi:

   pip install -r requirements.txt

Menjalankan aplikasi (lokal)
-----------------------------
Jalankan server untuk pengembangan lokal:

Windows:

   python run.py

Linux / macOS:

   python run.py

Akses aplikasi di http://127.0.0.1:5000/ setelah server berjalan.

Struktur proyek singkat
-----------------------
- app/: kode aplikasi (routes, templates, services)
- app/templates/: file template Jinja2
- app/static/: CSS, JS, gambar
- data/: database lokal (app.db)
- temp/: file sementara dan log runtime
- tests/: unit tests
- requirements.txt: daftar dependensi
- run.py: entrypoint aplikasi

Catatan penting
--------------
- File di `data/` dan `temp/` biasanya bersifat lokal; pastikan `.gitignore` diatur jika tidak ingin ikut ter-commit.
- `.gitignore` sudah mencakup pola umum seperti `*.xlsx`, `*.bat`, `*.md`, `*.txt`, `*.exe`, dan `__pycache__/`.

Kontribusi
----------
- Buat issue untuk masalah atau fitur baru.
- Buat branch baru untuk perubahan dan kirim pull request.

Kontak
------
Pemilik proyek: @leonxlab
