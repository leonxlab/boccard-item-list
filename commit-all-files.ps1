# commit-all-files.ps1
# Jalankan dari root folder repo: item-list-revision
# Setiap file di-commit terpisah dengan pesan commit sendiri.
# Kalau ada baris yang muncul "nothing to commit" -> aman, artinya file itu
# sudah ter-commit sebelumnya dengan isi yang sama. Skrip akan lanjut jalan.

git add .gitignore
git commit -m "Update ignore rules for generated and temp files"

git add app/__init__.py
git commit -m "Initialize Flask app package"

git add app/routes.py
git commit -m "Refine routing and page navigation logic"

git add app/services/__init__.py
git commit -m "Create services package initializer"

git add app/services/db_service.py
git commit -m "Add database service helper functions"

git add app/services/excel_service.py
git commit -m "Add Excel service for import/export operations"

git add app/static/css/style.css
git commit -m "Update stylesheet for sticky header and content layout"

git add app/static/favicon.ico
git commit -m "Include application favicon"

git add app/static/images/logo.png
git commit -m "Add main application logo"

git add app/static/images/white-logo.png
git commit -m "Add white logo asset"

git add app/static/js/app.js
git commit -m "Improve tab behavior and dialog interactions"

git add app/templates/404.html
git commit -m "Add custom 404 error page"

git add app/templates/base.html
git commit -m "Update base layout and sidebar navigation"

git add app/templates/edit.html
git commit -m "Revise edit page UI"

git add app/templates/index.html
git commit -m "Refine index page table layout"

git add app/templates/system.html
git commit -m "Update system information template"

git add app/templates/table.html
git commit -m "Update table display template"

git add app/templates/tabs.html
git commit -m "Update tabs page layout"

git add data/app.db
git commit -m "Include current local database snapshot"

git add requirements.txt
git commit -m "Update Python dependency requirements"

git add run.py
git commit -m "Update application startup script"

git add temp/1.json
git commit -m "Add temporary app data snapshot 1"

git add temp/2.json
git commit -m "Add temporary app data snapshot 2"

git add temp/3.json
git commit -m "Add temporary app data snapshot 3"

git add temp/5.json
git commit -m "Add temporary app data snapshot 5"

git add temp/7.json
git commit -m "Add temporary app data snapshot 7"

git add temp/8.json
git commit -m "Add temporary app data snapshot 8"

git add temp/10.json
git commit -m "Add temporary app data snapshot 10"

git add temp/11.json
git commit -m "Add temporary app data snapshot 11"

git add temp/12.json
git commit -m "Add temporary app data snapshot 12"

git add temp/device-9166ca-20260716T083512917776-12.json
git commit -m "Add device data snapshot 12"

git add temp/device-9166ca-20260716T085101471946-13.json
git commit -m "Add device data snapshot 13 (085101)"

git add temp/device-9166ca-20260716T085143316782-13.json
git commit -m "Add device data snapshot 13 (085143)"

git add temp/server-5000-20260716-135751.err.log
git commit -m "Add temp server error log from 135751"

git add temp/server-5000-20260716-135751.out.log
git commit -m "Add temp server output log from 135751"

git add temp/server-5000-20260716-135819.err.log
git commit -m "Add temp server error log from 135819"

git add temp/server-5000-20260716-135819.out.log
git commit -m "Add temp server output log from 135819"

git add temp/server-5000-20260716-140046.err.log
git commit -m "Add temp server error log from 140046"

git add temp/server-5000-20260716-140046.out.log
git commit -m "Add temp server output log from 140046"

git add temp/server-5000-20260716-142744.err.log
git commit -m "Add temp server error log from 142744"

git add temp/server-5000-20260716-142744.out.log
git commit -m "Add temp server output log from 142744"

git add temp/server-5000-20260716-143057.err.log
git commit -m "Add temp server error log from 143057"

git add temp/server-5000-20260716-143057.out.log
git commit -m "Add temp server output log from 143057"

git add temp/server-5000-20260716-144521.err.log
git commit -m "Add temp server error log from 144521"

git add temp/server-5000-20260716-144521.out.log
git commit -m "Add temp server output log from 144521"

git add temp/server-5000-20260716-145318.err.log
git commit -m "Add temp server error log from 145318"

git add temp/server-5000-20260716-145318.out.log
git commit -m "Add temp server output log from 145318"

git add temp/server-5000-20260716-145639.err.log
git commit -m "Add temp server error log from 145639"

git add temp/server-5000-20260716-145639.out.log
git commit -m "Add temp server output log from 145639"

git add temp/server-5000-20260716-151721.err.log
git commit -m "Add temp server error log from 151721"

git add temp/server-5000-20260716-151721.out.log
git commit -m "Add temp server output log from 151721"

git add temp/server-5000-20260716-153445.err.log
git commit -m "Add temp server error log from 153445"

git add temp/server-5000-20260716-153445.out.log
git commit -m "Add temp server output log from 153445"

git add temp/server-5000-20260716-154929.err.log
git commit -m "Add temp server error log from 154929"

git add temp/server-5000-20260716-154929.out.log
git commit -m "Add temp server output log from 154929"

# --- file log baru yang muncul hari ini (17 Juli), belum ada di daftar lama ---
git add temp/server-5000-20260717-091322.err.log
git commit -m "Add temp server error log from 20260717-091322"

git add temp/server-5000-20260717-091322.out.log
git commit -m "Add temp server output log from 20260717-091322"

git add temp/server-5000-latest.err.log
git commit -m "Add latest temp server error log"

git add temp/server-5000-latest.out.log
git commit -m "Add latest temp server output log"

git add temp/server-5000.err.log
git commit -m "Add temp server error log"

git add temp/server-5000.out.log
git commit -m "Add temp server output log"

git add temp/server-5001-latest.err.log
git commit -m "Add server-5001 latest error log"

git add temp/server-5001-latest.out.log
git commit -m "Add server-5001 latest output log"

git add tests/test_excel_service.py
git commit -m "Add Excel service test coverage"

git add white-logo.png
git commit -m "Add secondary white logo image"

# --- setelah semua commit selesai, push ke GitHub ---
git push -u origin main
