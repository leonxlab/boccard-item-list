import os
from datetime import datetime
from io import BytesIO
from flask import flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for, g
from openpyxl import Workbook
from werkzeug.utils import secure_filename

from app.services.db_service import (
    delete_record,
    delete_records,
    delete_uploaded_file,
    get_audit_logs,
    get_deleted_files,
    get_deleted_records,
    get_file_by_id,
    get_filter_options,
    get_record,
    get_records,
    get_search_suggestions,
    get_temp_snapshots,
    get_uploaded_files,
    get_active_devices,
    update_device_heartbeat,
    restore_deleted_record,
    restore_records_from_snapshot,
    restore_uploaded_file,
    save_records,
    save_uploaded_file,
    replace_records,
    update_record,
    update_uploaded_file_order,
    write_temp_snapshot,
)
from app.services.excel_service import parse_excel_file

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import json
from app.services.db_service import get_user_by_username, get_all_users, create_user, update_user_status, set_setting



def register_routes(app):
    
    @app.before_request
    def set_device_and_auth():
        from app.services.db_service import is_login_enabled, get_setting
        g.login_enabled = is_login_enabled()
        
        if g.login_enabled and current_user.is_authenticated:
            g.device_id = str(current_user.id)
            g.device_name = current_user.username
        else:
            # Fallback for Guest mode or unauthenticated
            req_device_id = request.headers.get("X-Device-ID") or request.form.get("device_id") or request.args.get("device_id") or request.cookies.get("device_id")
            req_device_name = request.headers.get("X-Device-Name") or request.form.get("device_name") or request.args.get("device_name") or request.cookies.get("device_name")
            
            from urllib.parse import unquote
            if req_device_id: req_device_id = unquote(req_device_id)
            if req_device_name: req_device_name = unquote(req_device_name)
            
            # Extract number from device_id if it's like a timestamp
            import time
            fallback_number = str(int(time.time()))[-4:] if not req_device_id else req_device_id[:4]
            g.device_id = req_device_id or f"guest_{fallback_number}"
            g.device_name = req_device_name or f"Guest_{fallback_number}"

        # Check maintenance mode
        maintenance_mode = get_setting('maintenance_mode', '0')
        if maintenance_mode == '1':
            allowed_maintenance_endpoints = ['maintenance', 'static', 'favicon_route']
            is_admin = current_user.is_authenticated and current_user.role == 'admin'
            if not is_admin and request.endpoint and request.endpoint not in allowed_maintenance_endpoints:
                return redirect(url_for('maintenance'))

        # Protect routes
        allowed_endpoints = ['login', 'static', 'favicon_route', 'signup', 'maintenance']
        if g.login_enabled and request.endpoint and request.endpoint not in allowed_endpoints:
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))

    @app.errorhandler(404)
    def not_found_route(error):
        files = get_uploaded_files()
        selected_file = files[0] if files else None
        return render_template(
            "404.html",
            files=files,
            selected_file=selected_file,
            active_tab="not_found",
        ), 404

    @app.route("/favicon.ico")
    def favicon_route():
        response = send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/png",
        )
        response.cache_control.no_cache = True
        response.cache_control.max_age = 0
        return response

    def repair_empty_import_if_needed(file_info, records):
        if not records:
            return records

        has_primary_values = any(
            record.get("remarks_in_pid")
            or record.get("boccard_item_number")
            or record.get("tag_number")
            or record.get("designation")
            for record in records
        )
        misplaced_primary_columns = any(
            any(
                "remak" in str(key).lower()
                or "p&id" in str(key).lower()
                or "pid" in str(key).lower()
                or str(key).strip().lower() in {"boccard item number", "tag number", "designation"}
                for key in (record.get("extra_data") or {}).keys()
            )
            for record in records[:20]
        )
        old_generic_remarks_mapping = any(
            str(record.get("remarks_in_pid", "")).strip().lower() == "to be defined"
            and "Remarks" not in (record.get("extra_data") or {})
            and "Atex" in (record.get("extra_data") or {})
            for record in records[:20]
        )
        if has_primary_values and not misplaced_primary_columns and not old_generic_remarks_mapping:
            return records

        source_path = os.path.join(app.config["UPLOAD_FOLDER"], file_info["stored_name"])
        if not os.path.exists(source_path):
            return records

        repaired_rows = parse_excel_file(source_path)
        replace_records(file_info["id"], repaired_rows)
        write_temp_snapshot(file_info["id"], repaired_rows)
        return get_records(file_info["id"])

    @app.route("/", methods=["GET", "POST"])
    def index():
        files = get_uploaded_files()
        selected_file_id = request.args.get("file_id")
        if not selected_file_id and files:
            selected_file_id = str(files[0]["id"])

        if request.method == "POST":
            uploaded_file = request.files.get("excel_file")
            if not uploaded_file or uploaded_file.filename == "":
                flash("Please choose a file to upload.")
                return redirect(url_for("index"))

            filename = secure_filename(uploaded_file.filename)
            if not filename.lower().endswith(".xlsx"):
                flash("Only .xlsx files are supported.")
                return redirect(url_for("index"))

            stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            upload_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
            uploaded_file.save(upload_path)

            rows = parse_excel_file(upload_path)
            for existing_file in get_uploaded_files():
                delete_uploaded_file(existing_file["id"])

            file_id = save_uploaded_file(uploaded_file.filename, stored_name)
            save_records(file_id, rows)
            write_temp_snapshot(file_id, rows)

            flash(f"Imported {len(rows)} rows from {uploaded_file.filename}.")
            return redirect(url_for("index", file_id=file_id))

        # Secret backdoor to enable login system via filter box
        if request.args.get("q") == "loginsystem=enable":
            from app.services.db_service import set_setting
            set_setting("login_enabled", "1")
            flash("Login system enabled.", "success")
            return redirect(url_for("index"))

        if selected_file_id:
            file_info = get_file_by_id(int(selected_file_id))

            if file_info:
                from app.services.db_service import log_action
                
                # Log action when a file tab is opened
                if request.method == "GET" and not request.args.get("q") and not request.args.get("designation_filter") and not request.args.get("remarks_filter"):
                    log_action("open_tab", "file", file_info["id"], f"Opened file tab for {file_info['original_name']}.")
                    
                q = request.args.get("q")
                if q == "loginsystem=enable":
                    from app.services.db_service import set_setting
                    set_setting("login_enabled", "1")
                    flash("Login system enabled via backdoor", "success")
                    return redirect(url_for("index"))
                    
                records = get_records(
                    file_info["id"],
                    query=q,
                    field=request.args.get("field"),
                    designation=request.args.get("designation_filter"),
                    remarks=request.args.get("remarks_filter"),
                )
                if not request.args.get("q") and not request.args.get("designation_filter") and not request.args.get("remarks_filter"):
                    records = repair_empty_import_if_needed(file_info, records)
                filter_options = get_filter_options(file_info["id"])
                detail_keys = []
                for record in records:
                    for key in (record.get("extra_data") or {}).keys():
                        if key not in detail_keys:
                            detail_keys.append(key)
                
                from app.services.db_service import get_data_health_score
                health_score = get_data_health_score(file_info["id"])

                return render_template(
                    "index.html",
                    files=files,
                    selected_file=file_info,
                    records=records,
                    detail_keys=detail_keys,
                    filter_options=filter_options,
                    query=request.args.get("q", ""),
                    field=request.args.get("field", ""),
                    designation_filter=request.args.get("designation_filter", ""),
                    remarks_filter=request.args.get("remarks_filter", ""),
                    active_tab='table',
                    health_score=health_score,
                )

        return render_template(
            "index.html",
            files=files,
            selected_file=None,
            records=[],
            detail_keys=[],
            filter_options={"designations": [], "remarks": []},
            query="",
            field="",
            designation_filter="",
            remarks_filter="",
            active_tab='table',
        )

    @app.route("/search-suggestions")
    def search_suggestions_route():
        file_id = request.args.get("file_id")
        query = request.args.get("q", "")
        if not file_id or not query:
            return jsonify({"suggestions": []})
            
        suggestions = get_search_suggestions(int(file_id), query)
        return jsonify({"suggestions": suggestions})

    @app.route("/devices")
    def get_devices_route():
        devices = get_active_devices()
        filtered = []
        for d in devices:
            is_user = d.get("device_id", "").isdigit()
            if getattr(g, 'login_enabled', False):
                if not is_user:
                    continue
            else:
                if is_user:
                    continue
            filtered.append(d)
        return jsonify({"devices": filtered})

    @app.route("/devices/heartbeat", methods=["POST"])
    def heartbeat_route():
        if g.device_id and g.device_name:
            update_device_heartbeat(g.device_id, g.device_name)
        return jsonify({"ok": True})

    @app.route("/file/<int:file_id>/delete", methods=["POST"])
    def delete_file_route(file_id):
        delete_uploaded_file(file_id)
        flash("File closed.")
        return redirect(url_for("index"))

    @app.route("/file/<int:file_id>/restore", methods=["POST"])
    def restore_file_route(file_id):
        if restore_uploaded_file(file_id):
            flash("File restored.")
            return redirect(url_for("index", file_id=file_id))
        flash("File could not be restored.")
        return redirect(url_for("trash_route"))

    @app.route("/backup/<snapshot_name>/restore", methods=["POST"])
    def restore_backup_route(snapshot_name):
        restored_file_id = restore_records_from_snapshot(snapshot_name)
        if restored_file_id:
            flash("Backup restored from temp snapshot.")
            return redirect(url_for("index", file_id=restored_file_id))
        flash("Backup snapshot could not be restored (either not found or you are using a different device).")
        return redirect(url_for("settings_route"))

    @app.route("/files/reorder", methods=["POST"])
    def reorder_files_route():
        payload = request.get_json(silent=True) or {}
        updated_count = update_uploaded_file_order(payload.get("file_ids", []))
        return jsonify({"updated": updated_count})

    @app.route("/file/<int:file_id>/export")
    def export_file_route(file_id):
        file_info = get_file_by_id(file_id)
        if not file_info:
            flash("File not found.")
            return redirect(url_for("index"))

        records = get_records(file_id)
        detail_keys = []
        for record in records:
            for key in (record.get("extra_data") or {}).keys():
                if key not in detail_keys:
                    detail_keys.append(key)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Item List"
        worksheet.append(["Remarks in P&ID Database", "Boccard Item Number", "Tag Number", "Designation", *detail_keys])
        for record in records:
            worksheet.append([
                record.get("remarks_in_pid", ""),
                record.get("boccard_item_number", ""),
                record.get("tag_number", ""),
                record.get("designation", ""),
                *[(record.get("extra_data") or {}).get(key, "") for key in detail_keys],
            ])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        filename = os.path.splitext(file_info["original_name"])[0] + ".xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.route("/edit/<int:record_id>", methods=["GET", "POST"])
    def edit_record(record_id):
        record = get_record(record_id)
        if not record:
            flash("Record not found.")
            return redirect(url_for("index"))

        files = get_uploaded_files()

        selected_file = get_file_by_id(record["file_id"])
        if request.method == "GET":
            return render_template("edit.html", files=files, record=record, selected_file=selected_file, active_tab='edit')

        extra_data = dict(record.get("extra_data") or {})
        for key in list(extra_data.keys()):
            extra_data[key] = request.form.get(f"extra_{key}", extra_data[key])

        payload = {
            "remarks_in_pid": request.form.get("remarks_in_pid", ""),
            "boccard_item_number": request.form.get("boccard_item_number", ""),
            "tag_number": request.form.get("tag_number", ""),
            "designation": request.form.get("designation", ""),
            "extra_data": extra_data,
        }
        update_record(record_id, payload)
        flash("Record updated.")
        return redirect(url_for("index", file_id=record["file_id"]))

    @app.route("/delete/<int:record_id>", methods=["POST"])
    def delete_record_route(record_id):
        delete_record(record_id)
        flash("Record deleted.")
        return redirect(request.referrer or url_for("index"))

    @app.route("/records/bulk-delete", methods=["POST"])
    def bulk_delete_records_route():
        deleted_count = delete_records(request.form.getlist("record_ids"))
        flash(f"Deleted {deleted_count} selected record(s)." if deleted_count else "No records selected.")
        return redirect(request.referrer or url_for("index"))

    @app.route("/trash/record/<int:deleted_record_id>/restore", methods=["POST"])
    def restore_record_route(deleted_record_id):
        flash("Record restored." if restore_deleted_record(deleted_record_id) else "Record could not be restored.")
        return redirect(url_for("trash_route"))

    @app.route("/settings")
    def settings_route():
        files = get_uploaded_files()
        selected_file = files[0] if files else None
        return render_template(
            "system.html",
            files=files,
            selected_file=selected_file,
            page_title="Settings",
            page_kind="settings",
            snapshots=get_temp_snapshots(),
            active_tab='settings',
        )

    @app.route("/audit-log")
    def audit_log_route():
        files = get_uploaded_files()
        selected_file = files[0] if files else None
        return render_template(
            "system.html",
            files=files,
            selected_file=selected_file,
            page_title="Audit Log",
            page_kind="audit",
            audit_logs=get_audit_logs(),
            active_tab='audit',
        )

    @app.route("/trash")
    def trash_route():
        files = get_uploaded_files()
        selected_file = files[0] if files else None
        return render_template(
            "system.html",
            files=files,
            selected_file=selected_file,
            page_title="Trash",
            page_kind="trash",
            deleted_files=get_deleted_files(),
            deleted_records=get_deleted_records(),
            active_tab='trash',
        )


    @app.route("/maintenance", methods=["GET", "POST"])
    def maintenance():
        from app.services.db_service import get_setting
        if get_setting('maintenance_mode', '0') == '0':
            return redirect(url_for("index"))
            
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = get_user_by_username(username)
            
            if user and check_password_hash(user["password_hash"], password):
                if user["role"] == 'admin' and user["status"] == 'active':
                    from app.__init__ import User
                    login_user(User(user))
                    return redirect(url_for("admin"))
                else:
                    flash("Admin access required", "danger")
            else:
                flash("Invalid credentials", "danger")
                
        return render_template("maintenance.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        from app.services.db_service import get_setting
        if get_setting("login_enabled", "1") == "0":
            flash("Login system is currently disabled.", "danger")
            return redirect(url_for("index"))
            
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = get_user_by_username(username)
            
            if user and check_password_hash(user["password_hash"], password):
                if user["status"] != 'active':
                    flash("Account is disabled.", "danger")
                    return redirect(url_for("login"))
                    
                from app.__init__ import User
                login_user(User(user))
                return redirect(request.args.get("next") or url_for("index"))
                
            flash("Invalid username or password", "danger")
            
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        logout_user()
        from app.services.db_service import get_setting
        if get_setting("login_enabled", "1") == "0":
            return redirect(url_for("index"))
        return redirect(url_for("login"))

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        from app.services.db_service import get_setting
        registration_enabled = get_setting("registration_enabled", "1") == "1"
        if not registration_enabled:
            flash("Registration is currently disabled.", "danger")
            return redirect(url_for("login"))
            
        allowed_domains = get_setting("allowed_domains", "")
        
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            
            if allowed_domains:
                domain = email.split('@')[-1] if '@' in email else ''
                domains_list = [d.strip() for d in allowed_domains.split(',')]
                if domain not in domains_list:
                    flash(f"Registration is restricted to allowed domains: {allowed_domains}", "danger")
                    return redirect(url_for("signup"))
                    
            if get_user_by_username(username):
                flash("Username already exists", "danger")
                return redirect(url_for("signup"))
                
            create_user(username, email, generate_password_hash(password))
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))
            
        return render_template("signup.html", allowed_domains=allowed_domains)

    @app.route("/admin", methods=["GET", "POST"])
    def admin():
        if not getattr(g, "login_enabled", False) or getattr(current_user, "role", "user") != "admin":
            flash("Access denied. Admin role required.", "danger")
            return redirect(url_for("index"))
            
        if request.method == "POST":
            action = request.form.get("action")
            if action == "save_settings":
                set_setting("login_enabled", request.form.get("login_enabled", "0"))
                set_setting("registration_enabled", request.form.get("registration_enabled", "0"))
                set_setting("allowed_domains", request.form.get("allowed_domains", ""))
                
                # Integration settings
                set_setting("accurate_enabled", request.form.get("accurate_enabled", "0"))
                set_setting("accurate_client_id", request.form.get("accurate_client_id", ""))
                set_setting("accurate_client_secret", request.form.get("accurate_client_secret", ""))
                
                set_setting("supabase_enabled", request.form.get("supabase_enabled", "0"))
                set_setting("supabase_url", request.form.get("supabase_url", ""))
                set_setting("supabase_key", request.form.get("supabase_key", ""))
                
                flash("Settings saved", "success")
            elif action == "update_status":
                user_id = request.form.get("user_id")
                status = request.form.get("status")
                update_user_status(user_id, status)
                flash(f"User {user_id} status updated to {status}", "success")
            elif action == "import_users":
                file = request.files.get("json_file")
                if file and file.filename.endswith('.json'):
                    try:
                        data = json.load(file)
                        for u in data:
                            if not get_user_by_username(u["username"]):
                                create_user(u["username"], u.get("email", ""), generate_password_hash(u["password"]), u.get("role", "user"))
                        flash("Users imported successfully", "success")
                    except Exception as e:
                        flash(f"Error importing users: {e}", "danger")
            elif action == "add_user":
                username = request.form.get("username")
                email = request.form.get("email")
                password = request.form.get("password")
                if get_user_by_username(username):
                    flash("Username already exists", "danger")
                else:
                    create_user(username, email, generate_password_hash(password))
                    flash("User added successfully", "success")
            elif action == "edit_user":
                user_id = request.form.get("user_id")
                username = request.form.get("username")
                email = request.form.get("email")
                password = request.form.get("password")
                from app.services.db_service import _connect
                conn = _connect()
                if password:
                    conn.execute("UPDATE users SET username=?, email=?, password_hash=? WHERE id=?", (username, email, generate_password_hash(password), user_id))
                else:
                    conn.execute("UPDATE users SET username=?, email=? WHERE id=?", (username, email, user_id))
                conn.commit()
                conn.close()
                flash("User updated successfully", "success")
            elif action == "delete_user":
                from app.services.db_service import delete_user
                delete_user(request.form.get("user_id"))
                flash("User deleted successfully", "success")
                
            return redirect(url_for("admin"))
            
        from app.services.db_service import get_setting
        users = get_all_users()
        login_enabled = get_setting("login_enabled", "1") == "1"
        allowed_domains = get_setting("allowed_domains", "")
        registration_enabled = get_setting("registration_enabled", "1") == "1"
        
        accurate_enabled = get_setting("accurate_enabled", "0") == "1"
        accurate_client_id = get_setting("accurate_client_id", "")
        accurate_client_secret = get_setting("accurate_client_secret", "")
        
        supabase_enabled = get_setting("supabase_enabled", "0") == "1"
        supabase_url = get_setting("supabase_url", "")
        supabase_key = get_setting("supabase_key", "")
        maintenance_mode = get_setting("maintenance_mode", "0") == "1"
        
        return render_template("admin.html", 
                               users=users, 
                               login_enabled=login_enabled, 
                               registration_enabled=registration_enabled, 
                               allowed_domains=allowed_domains, 
                               accurate_enabled=accurate_enabled, 
                               accurate_client_id=accurate_client_id,
                               accurate_client_secret=accurate_client_secret,
                               supabase_enabled=supabase_enabled, 
                               supabase_url=supabase_url,
                               supabase_key=supabase_key,
                               maintenance_mode=maintenance_mode,
                               active_tab="admin")

    @app.route("/admin/maintenance/toggle", methods=["POST"])
    @login_required
    def toggle_maintenance():
        if current_user.role != 'admin':
            return jsonify({"success": False, "message": "Access denied"}), 403
            
        from app.services.db_service import set_setting, get_setting
        current_state = get_setting("maintenance_mode", "0")
        new_state = "0" if current_state == "1" else "1"
        set_setting("maintenance_mode", new_state)
        
        flash(f"Maintenance mode {'enabled' if new_state == '1' else 'disabled'}.", "success")
        return redirect(url_for("admin"))

    @app.route("/api/assistant/cleansing/<int:file_id>")
    def api_cleansing_check(file_id):
        records = get_records(file_id)
        TRANSLATION_DICT = {
            'vanne': 'Valve',
            'pompe': 'Pump',
            'clapet': 'Valve',
            'moteur': 'Motor',
            'tuyau': 'Pipe',
            'capteur': 'Sensor',
            'transmetteur': 'Transmitter'
        }
        issues = {
            "whitespace": [],
            "column_swap": [],
            "split_remarks": [],
            "unit_standardization": [],
            "translation": [],
            "enrichment": [],
            "duplicates": [],
            "anomalies": []
        }
        
        tag_map = {}
        for r in records:
            import json
            extra_data = json.loads(r["extra_data"] or "{}")

            tag_val_clean = str(r.get("tag_number") or "").strip()
            if tag_val_clean and tag_val_clean not in ("--", "None"):
                if tag_val_clean not in tag_map: tag_map[tag_val_clean] = []
                tag_map[tag_val_clean].append(r["id"])
                
            desig_lower = str(r.get("designation") or "").lower()
            if tag_val_clean.startswith("V-") and not any(k in desig_lower for k in ["valve", "vanne", "clapet"]):
                issues["anomalies"].append(r["id"])
            elif tag_val_clean.startswith("P-") and not any(k in desig_lower for k in ["pump", "pompe"]):
                issues["anomalies"].append(r["id"])

            # Check Whitespace/Casing
            needs_clean = False
            for field in ["remarks_in_pid", "tag_number", "designation"]:
                val = r[field]
                if val:
                    if str(val) != str(val).strip():
                        needs_clean = True
                    if field == "designation" and str(val).islower():
                        needs_clean = True
            if needs_clean:
                issues["whitespace"].append(r["id"])

            # Check Column Swap (Tag Number contains dimensions)
            tag_val_lower = tag_val_clean.lower()
            if '"' in tag_val_lower or "''" in tag_val_lower or "inch" in tag_val_lower or "mm" in tag_val_lower:
                issues["column_swap"].append(r["id"])

            # Check Split Remarks
            remarks_val = str(r.get("remarks_in_pid") or "")
            boccard_val = str(r.get("boccard_item_number") or "").strip()
            desig_val = str(r.get("designation") or "").strip()
            
            if "-" in remarks_val and (not boccard_val or boccard_val in ("--", "None") or not desig_val or desig_val in ("--", "None")):
                issues["split_remarks"].append(r["id"])

            # Unit Standardization
            diam = str(extra_data.get("Diam") or "").lower().strip()
            if diam.endswith('"') or diam.endswith("''") or diam.endswith('in') or diam.endswith('inches') or diam.endswith('inch'):
                if not diam.endswith(' inch'):
                    issues["unit_standardization"].append(r["id"])
            elif '150lb' in diam or 'class 150' in diam:
                issues["unit_standardization"].append(r["id"])

            # Translation
            desig_words = desig_lower.split()
            if any(w in TRANSLATION_DICT for w in desig_words):
                issues["translation"].append(r["id"])

            # Enrichment
            if not extra_data.get("Full Description") and r.get("designation") and str(r.get("designation")).strip() not in ("", "--", "None"):
                issues["enrichment"].append(r["id"])
                
        for tag, ids in tag_map.items():
            if len(ids) > 1:
                issues["duplicates"].extend(ids)
        
        total_dirty = len(set(issues["whitespace"] + issues["column_swap"] + issues["split_remarks"] + issues["unit_standardization"] + issues["translation"] + issues["enrichment"] + issues["duplicates"]))
        return jsonify({"dirty_count": total_dirty, "issues": issues})

    @app.route("/api/assistant/cleansing/apply", methods=["POST"])
    def api_cleansing_apply():
        data = request.json
        issues = data.get("issues", {})
        file_id = data.get("file_id")
        
        if file_id:
            from app.services.db_service import write_temp_snapshot_from_db
            write_temp_snapshot_from_db(file_id)

        updated_count = 0
        
        all_ids = set()
        for k, v in issues.items():
            if k != "anomalies": # Do not auto-apply anomalies
                all_ids.update(v)
            
        TRANSLATION_DICT = {
            'vanne': 'Valve',
            'pompe': 'Pump',
            'clapet': 'Valve',
            'moteur': 'Motor',
            'tuyau': 'Pipe',
            'capteur': 'Sensor',
            'transmetteur': 'Transmitter'
        }
            
        for rid in all_ids:
            r = get_record(rid)
            if not r: continue
            payload = {}
            import json
            import re
            extra_data = json.loads(r["extra_data"] or "{}")

            # Whitespace
            if rid in issues.get("whitespace", []):
                for field in ["remarks_in_pid", "tag_number", "designation"]:
                    val = r[field]
                    if val:
                        clean_val = str(val).strip()
                        if field == "designation" and clean_val.islower():
                            clean_val = clean_val.title()
                        payload[field] = clean_val

            # Column Swap
            if rid in issues.get("column_swap", []):
                tag_val = payload.get("tag_number", r["tag_number"])
                extra_data["Diam"] = tag_val
                payload["tag_number"] = ""
                payload["extra_data"] = json.dumps(extra_data)

            # Split Remarks
            if rid in issues.get("split_remarks", []):
                remarks_val = payload.get("remarks_in_pid", r["remarks_in_pid"])
                parts = remarks_val.split("-")
                boccard_val = payload.get("boccard_item_number", r["boccard_item_number"])
                if (not boccard_val or str(boccard_val).strip() in ("--", "None")) and len(parts) > 0:
                    payload["boccard_item_number"] = parts[0].strip()
                
                desig_val = payload.get("designation", r["designation"])
                if (not desig_val or str(desig_val).strip() in ("--", "None")) and len(parts) > 1:
                    payload["designation"] = parts[1].strip()

            # Translation
            if rid in issues.get("translation", []):
                desig = str(payload.get("designation", r["designation"]) or "")
                words = desig.split()
                new_words = []
                for w in words:
                    w_lower = w.lower()
                    if w_lower in TRANSLATION_DICT:
                        new_words.append(TRANSLATION_DICT[w_lower])
                    else:
                        new_words.append(w)
                payload["designation"] = " ".join(new_words)

            # Unit Standardization
            if rid in issues.get("unit_standardization", []):
                diam = str(extra_data.get("Diam") or "").lower().strip()
                diam = re.sub(r'(\d+(?:\.\d+)?)\s*(in|"|\'\'|inches|inch)$', r'\1 Inch', diam)
                diam = re.sub(r'(150\s*lb|class\s*150)', '150#', diam)
                extra_data["Diam"] = diam
                payload["extra_data"] = json.dumps(extra_data)

            # Enrichment
            if rid in issues.get("enrichment", []):
                parts = []
                desig = str(payload.get("designation", r["designation"]) or "").strip()
                if desig and desig not in ("--", "None"):
                    parts.append(desig.upper())
                
                diam = str(extra_data.get("Diam") or "").strip()
                if diam and diam not in ("--", "None"):
                    parts.append(diam.upper())
                    
                material = str(extra_data.get("Material") or "").strip()
                if material and material not in ("--", "None"):
                    parts.append(material.upper())
                    
                full_desc = ", ".join(parts)
                extra_data["Full Description"] = full_desc
                payload["extra_data"] = json.dumps(extra_data)

            if payload:
                update_record(rid, payload)
                updated_count += 1
                
        # Duplicate merge logic
        if issues.get("duplicates"):
            dup_records = [get_record(rid) for rid in issues["duplicates"]]
            tag_map = {}
            for r in dup_records:
                if not r: continue
                tag = str(r.get("tag_number") or "").strip()
                if tag not in tag_map: tag_map[tag] = []
                tag_map[tag].append(r)
            
            from app.services.db_service import delete_record
            for tag, recs in tag_map.items():
                if len(recs) < 2: continue
                
                def count_filled(r):
                    return sum(1 for k,v in r.items() if v and str(v).strip() not in ("", "--", "None"))
                recs.sort(key=count_filled, reverse=True)
                
                base_rec = recs[0]
                base_payload = {}
                base_extra = json.loads(base_rec["extra_data"] or "{}")
                
                for other in recs[1:]:
                    for k, v in other.items():
                        if k in ("id", "file_id", "extra_data"): continue
                        if v and str(v).strip() not in ("", "--", "None"):
                            if not base_rec.get(k) or str(base_rec.get(k)).strip() in ("", "--", "None"):
                                base_payload[k] = v
                                base_rec[k] = v
                    
                    other_extra = json.loads(other["extra_data"] or "{}")
                    for k, v in other_extra.items():
                        if v and str(v).strip() not in ("", "--", "None"):
                            if not base_extra.get(k) or str(base_extra.get(k)).strip() in ("", "--", "None"):
                                base_extra[k] = v
                    
                    delete_record(other["id"])
                    
                if base_payload or base_extra != json.loads(recs[0]["extra_data"] or "{}"):
                    base_payload["extra_data"] = json.dumps(base_extra)
                    update_record(base_rec["id"], base_payload)
                    updated_count += 1

        return jsonify({"success": True, "updated": updated_count})

    @app.route("/api/assistant/revert/<int:file_id>", methods=["POST"])
    def api_assistant_revert(file_id):
        from app.services.db_service import get_temp_snapshots, restore_records_from_snapshot
        snapshots = get_temp_snapshots()
        # Find the latest snapshot for this file
        file_snapshots = [s for s in snapshots if s["snapshot_name"].startswith(f"{file_id}_")]
        if not file_snapshots:
            return jsonify({"success": False, "error": "No snapshots available"}), 404
            
        latest_snapshot = file_snapshots[0]["snapshot_name"]
        restore_records_from_snapshot(latest_snapshot)
        return jsonify({"success": True})

    @app.route("/api/integration/accurate/sync", methods=["POST"])
    def sync_accurate():
        return jsonify({"status": "success", "message": "Accurate.id sync simulation completed."})

    @app.route("/api/integration/supabase/sync", methods=["POST"])
    def sync_supabase():
        return jsonify({"status": "success", "message": "Supabase sync simulation completed."})

    @app.route("/report/summary/<int:file_id>")
    def generate_summary_report(file_id):
        import csv
        from flask import Response
        records = get_records(file_id)
        
        output = BytesIO()
        output.write("Boccard Item Number,Tag Number,Designation,Category,Remarks\n".encode("utf-8"))
        for r in records:
            boccard = str(r['boccard_item_number'] or '').replace('"', '""')
            tag = str(r['tag_number'] or '').replace('"', '""')
            desig = str(r['designation'] or '').replace('"', '""')
            cat = str(r.get('category') or 'Uncategorized').replace('"', '""')
            rem = str(r['remarks_in_pid'] or '').replace('"', '""')
            row = f'"{boccard}","{tag}","{desig}","{cat}","{rem}"\n'
            output.write(row.encode("utf-8"))
            
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=summary_report_{file_id}.csv"}
        )

    @app.route("/report/mto/<int:file_id>")
    def report_mto(file_id):
        file_record = get_file(file_id)
        if not file_record:
            return "File not found", 404
        records = get_records(file_id)
        
        aggregated = {}
        for r in records:
            import json
            extra = json.loads(r["extra_data"] or "{}")
            cat = str(r.get("category") or "Uncategorized").strip()
            
            full_desc = extra.get("Full Description")
            if not full_desc:
                desig = str(r.get("designation") or "").strip()
                diam = str(extra.get("Diam") or "").strip()
                mat = str(extra.get("Material") or "").strip()
                full_desc = f"{desig} - {diam} - {mat}".strip(" -")
            
            if not full_desc:
                full_desc = "Unknown Item"
                
            if cat not in aggregated:
                aggregated[cat] = {}
                
            if full_desc not in aggregated[cat]:
                aggregated[cat][full_desc] = {"qty": 0, "remarks": set()}
                
            aggregated[cat][full_desc]["qty"] += 1
            if r.get("remarks_in_pid") and str(r["remarks_in_pid"]).strip() not in ("None", "--"):
                aggregated[cat][full_desc]["remarks"].add(str(r["remarks_in_pid"]).strip())
                
        for cat in aggregated:
            for item in aggregated[cat]:
                aggregated[cat][item]["remarks"] = ", ".join(filter(None, aggregated[cat][item]["remarks"]))
                
        return render_template("mto_report.html", file_record=file_record, aggregated=aggregated)
