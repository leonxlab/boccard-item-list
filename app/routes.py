import os
from datetime import datetime
from io import BytesIO
from flask import flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
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
    get_temp_snapshots,
    get_uploaded_files,
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


def register_routes(app):
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

        if selected_file_id:
            file_info = get_file_by_id(int(selected_file_id))
            if file_info:
                records = get_records(
                    file_info["id"],
                    query=request.args.get("q"),
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

    @app.route("/backup/<int:file_id>/restore", methods=["POST"])
    def restore_backup_route(file_id):
        restored_file_id = restore_records_from_snapshot(file_id)
        if restored_file_id:
            flash("Backup restored from temp snapshot.")
            return redirect(url_for("index", file_id=restored_file_id))
        flash("Backup snapshot was not found.")
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
