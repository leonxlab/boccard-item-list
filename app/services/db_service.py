import json
import os
import sqlite3
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "app.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
TEMP_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")


def init_db(upload_folder=None, temp_folder=None):
    global DB_PATH, UPLOAD_FOLDER, TEMP_FOLDER
    if upload_folder:
        UPLOAD_FOLDER = upload_folder
    if temp_folder:
        TEMP_FOLDER = temp_folder

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            tab_order INTEGER NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'active'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            remarks_in_pid TEXT,
            boccard_item_number TEXT,
            tag_number TEXT,
            designation TEXT,
            extra_data TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deleted_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_record_id INTEGER NOT NULL,
            file_id INTEGER NOT NULL,
            file_name TEXT,
            payload TEXT NOT NULL,
            deleted_at TEXT NOT NULL
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(uploaded_files)").fetchall()}
    if "tab_order" not in columns:
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN tab_order INTEGER NOT NULL DEFAULT 0")
    if "status" not in columns:
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN status TEXT DEFAULT 'active'")
    if "deleted_at" not in columns:
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN deleted_at TEXT")

    ordered_rows = conn.execute(
        "SELECT id, tab_order FROM uploaded_files ORDER BY tab_order ASC, uploaded_at ASC, id ASC"
    ).fetchall()
    if ordered_rows and all(row["tab_order"] == 0 for row in ordered_rows):
        for index, row in enumerate(
            conn.execute("SELECT id FROM uploaded_files ORDER BY id DESC").fetchall()
        ):
            conn.execute("UPDATE uploaded_files SET tab_order = ? WHERE id = ?", (index, row["id"]))

    conn.commit()
    conn.close()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def log_action(action, entity_type, entity_id, message):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO audit_logs (action, entity_type, entity_id, message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (action, entity_type, entity_id, message, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def save_uploaded_file(original_name, stored_name):
    conn = _connect()
    now = datetime.utcnow().isoformat()
    next_order_row = conn.execute("SELECT COALESCE(MAX(tab_order), -1) + 1 AS next_order FROM uploaded_files").fetchone()
    next_order = next_order_row["next_order"] if next_order_row else 0
    cursor = conn.execute(
        "INSERT INTO uploaded_files (original_name, stored_name, uploaded_at, tab_order, status) VALUES (?, ?, ?, ?, ?)",
        (original_name, stored_name, now, next_order, "active"),
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_action("upload", "file", file_id, f"Uploaded workbook {original_name}.")
    return file_id


def save_records(file_id, rows):
    conn = _connect()
    now = datetime.utcnow().isoformat()
    for row in rows:
        conn.execute(
            """
            INSERT INTO records (file_id, remarks_in_pid, boccard_item_number, tag_number, designation, extra_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                row.get("remarks_in_pid", ""),
                row.get("boccard_item_number", ""),
                row.get("tag_number", ""),
                row.get("designation", ""),
                json.dumps(row.get("extra_data", {})),
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()


def replace_records(file_id, rows):
    conn = _connect()
    conn.execute("DELETE FROM records WHERE file_id = ?", (file_id,))
    now = datetime.utcnow().isoformat()
    for row in rows:
        conn.execute(
            """
            INSERT INTO records (file_id, remarks_in_pid, boccard_item_number, tag_number, designation, extra_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                row.get("remarks_in_pid", ""),
                row.get("boccard_item_number", ""),
                row.get("tag_number", ""),
                row.get("designation", ""),
                json.dumps(row.get("extra_data", {})),
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()


def write_temp_snapshot(file_id, rows):
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    snapshot_path = os.path.join(TEMP_FOLDER, f"{file_id}.json")
    with open(snapshot_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)


def write_temp_snapshot_from_db(file_id):
    rows = get_records(file_id)
    write_temp_snapshot(file_id, rows)
    return len(rows)


def get_temp_snapshots():
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    snapshots = []
    for name in os.listdir(TEMP_FOLDER):
        if not name.endswith(".json"):
            continue
        path = os.path.join(TEMP_FOLDER, name)
        try:
            file_id = int(os.path.splitext(name)[0])
        except ValueError:
            file_id = None
        snapshots.append(
            {
                "file_id": file_id,
                "name": name,
                "size": os.path.getsize(path),
                "updated_at": datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat(),
            }
        )
    return sorted(snapshots, key=lambda item: item["updated_at"], reverse=True)


def restore_records_from_snapshot(file_id):
    snapshot_path = os.path.abspath(os.path.join(TEMP_FOLDER, f"{file_id}.json"))
    temp_root = os.path.abspath(TEMP_FOLDER)
    if not snapshot_path.startswith(temp_root + os.sep) or not os.path.exists(snapshot_path):
        return None

    with open(snapshot_path, "r", encoding="utf-8") as handle:
        rows = json.load(handle)

    target_file = get_any_file_by_id(file_id)
    if target_file:
        replace_records(file_id, rows)
        restore_uploaded_file(file_id)
        restored_file_id = file_id
    else:
        restored_file_id = save_uploaded_file(f"Recovered backup {file_id}.xlsx", f"recovered_backup_{file_id}.json")
        save_records(restored_file_id, rows)
        write_temp_snapshot(restored_file_id, rows)

    log_action("restore_backup", "file", restored_file_id, f"Restored records from temp snapshot {file_id}.json.")
    return restored_file_id


def get_uploaded_files():
    conn = _connect()
    files = conn.execute("SELECT * FROM uploaded_files WHERE status = 'active' ORDER BY tab_order ASC, id ASC").fetchall()
    conn.close()
    return [dict(file) for file in files]


def get_file_by_id(file_id):
    conn = _connect()
    file_row = conn.execute("SELECT * FROM uploaded_files WHERE id = ? AND status = 'active'", (file_id,)).fetchone()
    conn.close()
    return dict(file_row) if file_row else None


def get_any_file_by_id(file_id):
    conn = _connect()
    file_row = conn.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    return dict(file_row) if file_row else None


def get_deleted_files():
    conn = _connect()
    files = conn.execute(
        "SELECT * FROM uploaded_files WHERE status = 'trashed' ORDER BY deleted_at DESC, id DESC"
    ).fetchall()
    conn.close()
    return [dict(file) for file in files]


def get_audit_logs(limit=200):
    conn = _connect()
    logs = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(log) for log in logs]


def delete_uploaded_file(file_id):
    conn = _connect()
    file_row = conn.execute("SELECT original_name FROM uploaded_files WHERE id = ?", (file_id,)).fetchone()
    if not file_row:
        conn.close()
        return
    conn.execute(
        "UPDATE uploaded_files SET status = 'trashed', deleted_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), file_id),
    )
    conn.commit()
    conn.close()
    write_temp_snapshot_from_db(file_id)
    log_action("trash_file", "file", file_id, f"Moved workbook {file_row['original_name']} to trash.")


def restore_uploaded_file(file_id):
    conn = _connect()
    file_row = conn.execute("SELECT original_name FROM uploaded_files WHERE id = ?", (file_id,)).fetchone()
    if not file_row:
        conn.close()
        return False
    conn.execute("UPDATE uploaded_files SET status = 'active', deleted_at = NULL WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    log_action("restore_file", "file", file_id, f"Restored workbook {file_row['original_name']} from trash.")
    return True


def update_uploaded_file_order(file_ids):
    ids = [int(file_id) for file_id in file_ids if str(file_id).isdigit()]
    if not ids:
        return 0

    conn = _connect()
    for index, file_id in enumerate(ids):
        conn.execute("UPDATE uploaded_files SET tab_order = ? WHERE id = ?", (index, file_id))
    conn.commit()
    conn.close()
    return len(ids)


def get_records(file_id, query=None, field=None, designation=None, remarks=None):
    conn = _connect()
    sql = "SELECT * FROM records WHERE file_id = ?"
    params = [file_id]

    if query:
        query_text = f"%{query}%"
        if field and field in {"remarks_in_pid", "boccard_item_number", "tag_number", "designation"}:
            sql += f" AND {field} LIKE ?"
            params.append(query_text)
        else:
            sql += " AND (remarks_in_pid LIKE ? OR boccard_item_number LIKE ? OR tag_number LIKE ? OR designation LIKE ?)"
            params.extend([query_text, query_text, query_text, query_text])

    if designation:
        sql += " AND designation = ?"
        params.append(designation)

    if remarks:
        sql += " AND remarks_in_pid = ?"
        params.append(remarks)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    for row in rows:
        item = dict(row)
        item["extra_data"] = json.loads(item["extra_data"] or "{}")
        result.append(item)
    return result


def get_filter_options(file_id):
    conn = _connect()
    designations = conn.execute(
        """
        SELECT DISTINCT designation
        FROM records
        WHERE file_id = ? AND designation IS NOT NULL AND TRIM(designation) != ''
        ORDER BY designation
        """,
        (file_id,),
    ).fetchall()
    remarks = conn.execute(
        """
        SELECT DISTINCT remarks_in_pid
        FROM records
        WHERE file_id = ? AND remarks_in_pid IS NOT NULL AND TRIM(remarks_in_pid) != ''
        ORDER BY remarks_in_pid
        """,
        (file_id,),
    ).fetchall()
    conn.close()

    return {
        "designations": [row["designation"] for row in designations],
        "remarks": [row["remarks_in_pid"] for row in remarks],
    }


def get_record(record_id):
    conn = _connect()
    row = conn.execute(
        """
        SELECT records.*, uploaded_files.original_name, uploaded_files.uploaded_at, uploaded_files.status
        FROM records
        JOIN uploaded_files ON uploaded_files.id = records.file_id
        WHERE records.id = ?
        """,
        (record_id,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    item["extra_data"] = json.loads(item["extra_data"] or "{}")
    return item


def update_record(record_id, payload):
    conn = _connect()
    now = datetime.utcnow().isoformat()
    existing = conn.execute("SELECT file_id FROM records WHERE id = ?", (record_id,)).fetchone()
    conn.execute(
        """
        UPDATE records
        SET remarks_in_pid = ?, boccard_item_number = ?, tag_number = ?, designation = ?, extra_data = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            payload.get("remarks_in_pid", ""),
            payload.get("boccard_item_number", ""),
            payload.get("tag_number", ""),
            payload.get("designation", ""),
            json.dumps(payload.get("extra_data", {})),
            now,
            record_id,
        ),
    )
    conn.commit()
    conn.close()
    if existing:
        row_count = write_temp_snapshot_from_db(existing["file_id"])
        log_action("update_record", "record", record_id, f"Updated record {record_id}. Snapshot now has {row_count} rows.")


def delete_record(record_id):
    conn = _connect()
    row = conn.execute(
        """
        SELECT records.*, uploaded_files.original_name
        FROM records
        LEFT JOIN uploaded_files ON uploaded_files.id = records.file_id
        WHERE records.id = ?
        """,
        (record_id,),
    ).fetchone()
    if not row:
        conn.close()
        return
    payload = dict(row)
    file_id = payload["file_id"]
    payload["extra_data"] = json.loads(payload.get("extra_data") or "{}")
    conn.execute(
        """
        INSERT INTO deleted_records (original_record_id, file_id, file_name, payload, deleted_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            record_id,
            file_id,
            payload.get("original_name"),
            json.dumps(payload),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    write_temp_snapshot_from_db(file_id)
    log_action("delete_record", "record", record_id, f"Moved record {record_id} to trash.")


def delete_records(record_ids):
    ids = [int(record_id) for record_id in record_ids if str(record_id).isdigit()]
    if not ids:
        return 0

    conn = _connect()
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT records.*, uploaded_files.original_name
        FROM records
        LEFT JOIN uploaded_files ON uploaded_files.id = records.file_id
        WHERE records.id IN ({placeholders})
        """,
        ids,
    ).fetchall()
    now = datetime.utcnow().isoformat()
    touched_file_ids = set()
    for row in rows:
        payload = dict(row)
        touched_file_ids.add(payload["file_id"])
        payload["extra_data"] = json.loads(payload.get("extra_data") or "{}")
        conn.execute(
            """
            INSERT INTO deleted_records (original_record_id, file_id, file_name, payload, deleted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload["id"], payload["file_id"], payload.get("original_name"), json.dumps(payload), now),
        )
    cursor = conn.execute(f"DELETE FROM records WHERE id IN ({placeholders})", ids)
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    for file_id in touched_file_ids:
        write_temp_snapshot_from_db(file_id)
    if deleted_count:
        log_action("bulk_delete_records", "record", None, f"Moved {deleted_count} records to trash.")
    return deleted_count


def get_deleted_records(limit=200):
    conn = _connect()
    rows = conn.execute("SELECT * FROM deleted_records ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"] or "{}")
        result.append(item)
    return result


def restore_deleted_record(deleted_record_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM deleted_records WHERE id = ?", (deleted_record_id,)).fetchone()
    if not row:
        conn.close()
        return False
    payload = json.loads(row["payload"] or "{}")
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        """
        INSERT INTO records (file_id, remarks_in_pid, boccard_item_number, tag_number, designation, extra_data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("file_id"),
            payload.get("remarks_in_pid", ""),
            payload.get("boccard_item_number", ""),
            payload.get("tag_number", ""),
            payload.get("designation", ""),
            json.dumps(payload.get("extra_data", {})),
            payload.get("created_at") or now,
            now,
        ),
    )
    conn.execute("DELETE FROM deleted_records WHERE id = ?", (deleted_record_id,))
    conn.commit()
    restored_id = cursor.lastrowid
    file_id = payload.get("file_id")
    conn.close()
    if file_id:
        write_temp_snapshot_from_db(file_id)
    log_action("restore_record", "record", restored_id, f"Restored deleted record {payload.get('id')}.")
    return True
