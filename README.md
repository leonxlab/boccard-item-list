# Item List Revision

Aplikasi web sederhana berbasis Flask untuk menampilkan, mengedit, dan mengelola daftar item, lengkap dengan layanan impor/ekspor Excel dan utilitas pengembangan lokal.

## Prasyarat

- Python 3.8 atau lebih baru
- pip

## Instalasi

1. Buka terminal pada folder project:

   ```
   cd C:\Users\manur\OneDrive\Documents\item-list-revision
   ```

2. (Opsional, disarankan) Buat virtual environment:

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Pasang dependensi:

   ```
   pip install -r requirements.txt
   ```

## Menjalankan Aplikasi (Lokal)

Jalankan server untuk pengembangan lokal (Windows, Linux, maupun macOS):

```
python run.py
```

Setelah server berjalan, akses aplikasi di:

```
http://127.0.0.1:5000/
```

## Struktur Proyek

```
item-list-revision/
├── app/                    # Kode aplikasi (routes, templates, services)
│   ├── templates/          # File template Jinja2
│   ├── static/             # CSS, JS, gambar
│   └── services/           # Logika bisnis (database, Excel import/export)
├── data/                   # Database lokal (app.db)
├── temp/                   # File sementara dan log runtime
├── tests/                  # Unit tests
├── requirements.txt        # Daftar dependensi Python
└── run.py                  # Entrypoint aplikasi
```

## Menjalankan Test

```
python -m pytest tests/
```

## Catatan Penting

- File di `data/` dan `temp/` bersifat lokal (database dan log runtime) dan sebaiknya tidak ikut ter-commit ke repository.
- `.gitignore` sudah mencakup pola umum seperti `*.xlsx`, `*.bat`, `*.md`, `*.txt`, `*.exe`, dan `__pycache__/`, dengan pengecualian untuk `requirements.txt` agar tetap dapat di-commit.

## Kontribusi

- Buat *issue* untuk melaporkan masalah atau mengusulkan fitur baru.
- Buat branch baru untuk setiap perubahan, lalu ajukan *pull request*.

## Kontak

Pemilik proyek: [@suboccard](http://github.com/suboccard/)
