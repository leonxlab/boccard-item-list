import json
import os
import sqlite3
from datetime import datetime
from flask import g
from werkzeug.security import generate_password_hash


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
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active'
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        '''
    )
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
            category TEXT,
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
            device_id TEXT,
            device_name TEXT,
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
        
    records_cols = {row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()}
    if 'category' not in records_cols:
        conn.execute("ALTER TABLE records ADD COLUMN category TEXT")

    # Ensure default admin exists
    admin = conn.execute("SELECT * FROM users WHERE username = 'suboccard'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("suboccard", "", generate_password_hash("admin"), "admin")
        )
        
    # Ensure default settings
    login_enabled = conn.execute("SELECT * FROM app_settings WHERE key = 'login_enabled'").fetchone()
    if not login_enabled:
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", ("login_enabled", "1"))

    audit_columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_logs)").fetchall()}
    if "device_id" not in audit_columns:
        conn.execute("ALTER TABLE audit_logs ADD COLUMN device_id TEXT")
    if "device_name" not in audit_columns:
        conn.execute("ALTER TABLE audit_logs ADD COLUMN device_name TEXT")

    if "user_id" not in audit_columns:
        conn.execute("ALTER TABLE audit_logs ADD COLUMN user_id INTEGER")
    if "user_name" not in audit_columns:
        conn.execute("ALTER TABLE audit_logs ADD COLUMN user_name TEXT")
        
    deleted_columns = {row[1] for row in conn.execute("PRAGMA table_info(deleted_records)").fetchall()}
    if "user_id" not in deleted_columns:
        conn.execute("ALTER TABLE deleted_records ADD COLUMN user_id INTEGER")
    if "user_name" not in deleted_columns:
        conn.execute("ALTER TABLE deleted_records ADD COLUMN user_name TEXT")


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


def get_current_device():
    try:
        return getattr(g, "device_id", None), getattr(g, "device_name", None)
    except RuntimeError:
        return None, None


def update_device_heartbeat(device_id, device_name):
    if not device_id:
        return
    
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    heartbeat_path = os.path.join(TEMP_FOLDER, "devices.json")
    
    devices = {}
    if os.path.exists(heartbeat_path):
        try:
            with open(heartbeat_path, "r", encoding="utf-8") as f:
                devices = json.load(f)
        except Exception:
            pass
            
    devices[device_id] = {
        "device_name": device_name,
        "last_seen": datetime.utcnow().isoformat()
    }
    
    with open(heartbeat_path, "w", encoding="utf-8") as f:
        json.dump(devices, f)


def get_active_devices():
    heartbeat_path = os.path.join(TEMP_FOLDER, "devices.json")
    if not os.path.exists(heartbeat_path):
        return []
        
    try:
        with open(heartbeat_path, "r", encoding="utf-8") as f:
            devices = json.load(f)
    except Exception:
        return []
        
    now = datetime.utcnow()
    results = []
    for d_id, info in devices.items():
        last_seen = datetime.fromisoformat(info["last_seen"])
        is_online = (now - last_seen).total_seconds() < 120 # 2 minutes
        results.append({
            "device_id": d_id,
            "device_name": info["device_name"],
            "online": is_online
        })
        
    # Sort online first, then by name
    return sorted(results, key=lambda x: (not x["online"], x["device_name"].lower()))


def log_action(action, entity_type, entity_id, message, device_id=None, device_name=None, user_id=None, user_name=None):
    if not device_id or not device_name:
        req_dev_id, req_dev_name = get_current_device()
        device_id = device_id or req_dev_id
        device_name = device_name or req_dev_name
        
    from flask_login import current_user
    try:
        if current_user.is_authenticated:
            user_id = user_id or current_user.id
            user_name = user_name or current_user.username
    except:
        pass

    conn = _connect()
    conn.execute(
        """
        INSERT INTO audit_logs (action, entity_type, entity_id, message, device_id, device_name, user_id, user_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (action, entity_type, entity_id, message, device_id, device_name, user_id, user_name, datetime.utcnow().isoformat()),
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
            INSERT INTO records (file_id, remarks_in_pid, boccard_item_number, tag_number, designation, category, extra_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                row.get("remarks_in_pid", ""),
                row.get("boccard_item_number", ""),
                row.get("tag_number", ""),
                row.get("designation", ""),
                row.get("category", "Uncategorized"),
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
            INSERT INTO records (file_id, remarks_in_pid, boccard_item_number, tag_number, designation, category, extra_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                row.get("remarks_in_pid", ""),
                row.get("boccard_item_number", ""),
                row.get("tag_number", ""),
                row.get("designation", ""),
                row.get("category", "Uncategorized"),
                json.dumps(row.get("extra_data", {})),
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()


def write_temp_snapshot(file_id, rows):
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    req_dev_id, req_dev_name = get_current_device()
    device_id = req_dev_id or "unknown"
    device_name = req_dev_name or "Unknown Device"
    
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f"backup_{device_id}_{file_id}_{timestamp}.json"
    snapshot_path = os.path.join(TEMP_FOLDER, filename)
    
    payload = {
        "device_id": device_id,
        "device_name": device_name,
        "file_id": file_id,
        "rows": rows
    }
    
    with open(snapshot_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        
    # Enforce max 3 backups per device
    all_backups = []
    for name in os.listdir(TEMP_FOLDER):
        if name.startswith(f"backup_{device_id}_") and name.endswith(".json"):
            path = os.path.join(TEMP_FOLDER, name)
            all_backups.append((path, os.path.getmtime(path)))
            
    all_backups.sort(key=lambda x: x[1], reverse=True)
    if len(all_backups) > 3:
        for backup_path, _ in all_backups[3:]:
            os.remove(backup_path)


def write_temp_snapshot_from_db(file_id):
    rows = get_records(file_id)
    write_temp_snapshot(file_id, rows)
    return len(rows)


def get_temp_snapshots():
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    snapshots = []
    for name in os.listdir(TEMP_FOLDER):
        if not name.endswith(".json") or name == "devices.json":
            continue
        path = os.path.join(TEMP_FOLDER, name)
        
        # Try to parse new format backup_{device_id}_{file_id}_{timestamp}.json
        parts = name.replace(".json", "").split("_")
        device_id = "unknown"
        device_name = "Unknown Device"
        file_id = None
        
        if len(parts) >= 4 and parts[0] == "backup":
            device_id = parts[1]
            try:
                file_id = int(parts[2])
            except ValueError:
                pass
            
            # Read payload for accurate device name if possible
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    device_name = data.get("device_name", device_name)
                    file_id = data.get("file_id", file_id)
            except Exception:
                pass
        else:
            try:
                file_id = int(os.path.splitext(name)[0])
            except ValueError:
                pass

        snapshots.append(
            {
                "snapshot_name": name,
                "file_id": file_id,
                "device_id": device_id,
                "device_name": device_name,
                "name": f"{device_name} ({device_id})" if device_id != "unknown" else name,
                "size": os.path.getsize(path),
                "updated_at": datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat(),
            }
        )
    return sorted(snapshots, key=lambda item: item["updated_at"], reverse=True)


def restore_records_from_snapshot(snapshot_name):
    snapshot_path = os.path.abspath(os.path.join(TEMP_FOLDER, snapshot_name))
    temp_root = os.path.abspath(TEMP_FOLDER)
    if not snapshot_path.startswith(temp_root + os.sep) or not os.path.exists(snapshot_path):
        return None

    with open(snapshot_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
        
    # Handle old format (raw list) vs new format (dict with payload)
    if isinstance(data, dict) and "rows" in data:
        rows = data["rows"]
        file_id = data.get("file_id")
        backup_device_id = data.get("device_id")
        
        req_dev_id, _ = get_current_device()
        if backup_device_id and req_dev_id and backup_device_id != req_dev_id:
            # Cannot restore backup from different device
            return None
    else:
        rows = data
        try:
            file_id = int(os.path.splitext(snapshot_name)[0])
        except ValueError:
            file_id = None

    target_file = get_any_file_by_id(file_id) if file_id else None
    if target_file:
        replace_records(file_id, rows)
        restore_uploaded_file(file_id)
        restored_file_id = file_id
    else:
        restored_file_id = save_uploaded_file(f"Recovered backup {snapshot_name}", f"recovered_{snapshot_name}")
        save_records(restored_file_id, rows)
        write_temp_snapshot(restored_file_id, rows)

    log_action("restore_backup", "file", restored_file_id, f"Restored records from temp snapshot {snapshot_name}.")
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
    
    # Enforce Max 10 trashed files
    trashed = conn.execute("SELECT id FROM uploaded_files WHERE status = 'trashed' ORDER BY deleted_at ASC").fetchall()
    if len(trashed) > 10:
        for idx in range(len(trashed) - 10):
            oldest_id = trashed[idx]["id"]
            conn.execute("DELETE FROM deleted_records WHERE file_id = ?", (oldest_id,))
            conn.execute("DELETE FROM uploaded_files WHERE id = ?", (oldest_id,))
            
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


def get_records(file_id, query=None, field=None, designation=None, remarks=None, tag_number=None):
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

    if tag_number:
        sql += " AND tag_number = ?"
        params.append(tag_number)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    for row in rows:
        item = dict(row)
        item["extra_data"] = json.loads(item["extra_data"] or "{}")
        result.append(item)
    return result

def get_data_health_score(file_id):
    conn = _connect()
    rows = conn.execute("SELECT boccard_item_number, tag_number, designation, extra_data FROM records WHERE file_id = ?", (file_id,)).fetchall()
    conn.close()

    if not rows:
        return 100

    total_fields = len(rows) * 4
    filled_fields = 0

    for row in rows:
        if row["boccard_item_number"] and str(row["boccard_item_number"]).strip() not in ("", "--", "None"):
            filled_fields += 1
        if row["tag_number"] and str(row["tag_number"]).strip() not in ("", "--", "None"):
            filled_fields += 1
        if row["designation"] and str(row["designation"]).strip() not in ("", "--", "None"):
            filled_fields += 1
            
        extra = json.loads(row["extra_data"] or "{}")
        if extra.get("Diam") and str(extra["Diam"]).strip() not in ("", "--", "None"):
            filled_fields += 1

    return int((filled_fields / total_fields) * 100)


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
    tag_numbers = conn.execute(
        """
        SELECT DISTINCT tag_number
        FROM records
        WHERE file_id = ? AND tag_number IS NOT NULL AND TRIM(tag_number) != ''
        ORDER BY tag_number
        """,
        (file_id,),
    ).fetchall()
    conn.close()

    return {
        "designations": [row["designation"] for row in designations],
        "remarks": [row["remarks_in_pid"] for row in remarks],
        "tag_numbers": [row["tag_number"] for row in tag_numbers],
    }


def get_values_for_designation(file_id, designation):
    conn = _connect()
    remarks_rows = conn.execute(
        """
        SELECT DISTINCT remarks_in_pid
        FROM records
        WHERE file_id = ? AND designation = ? AND remarks_in_pid IS NOT NULL AND TRIM(remarks_in_pid) != ''
        ORDER BY remarks_in_pid
        """,
        (file_id, designation),
    ).fetchall()
    boccard_rows = conn.execute(
        """
        SELECT DISTINCT boccard_item_number
        FROM records
        WHERE file_id = ? AND designation = ? AND boccard_item_number IS NOT NULL AND TRIM(boccard_item_number) != ''
        ORDER BY boccard_item_number
        """,
        (file_id, designation),
    ).fetchall()
    pair_rows = conn.execute(
        """
        SELECT DISTINCT boccard_item_number, remarks_in_pid
        FROM records
        WHERE file_id = ? AND designation = ?
            AND boccard_item_number IS NOT NULL AND TRIM(boccard_item_number) != ''
            AND remarks_in_pid IS NOT NULL AND TRIM(remarks_in_pid) != ''
        ORDER BY boccard_item_number
        """,
        (file_id, designation),
    ).fetchall()
    conn.close()

    return {
        "remarks": [row["remarks_in_pid"] for row in remarks_rows],
        "boccard_items": [row["boccard_item_number"] for row in boccard_rows],
        "pairs": [
            {"boccard_item_number": row["boccard_item_number"], "remarks_in_pid": row["remarks_in_pid"]}
            for row in pair_rows
        ],
    }


def get_search_suggestions(file_id, query, limit=8):
    if not query or len(query.strip()) < 1:
        return []
        
    conn = _connect()
    query_text = f"%{query.strip()}%"
    
    # Search in common fields
    rows = conn.execute(
        """
        SELECT remarks_in_pid, boccard_item_number, designation, extra_data
        FROM records 
        WHERE file_id = ? AND (
            remarks_in_pid LIKE ? OR 
            boccard_item_number LIKE ? OR 
            designation LIKE ? OR 
            extra_data LIKE ?
        )
        LIMIT 100
        """,
        (file_id, query_text, query_text, query_text, query_text)
    ).fetchall()
    conn.close()
    
    suggestions = set()
    query_lower = query.strip().lower()
    
    for row in rows:
        # Check designation
        val = str(row["designation"] or "").strip()
        if query_lower in val.lower():
            suggestions.add(val)
            
        # Check remarks
        val = str(row["remarks_in_pid"] or "").strip()
        if query_lower in val.lower():
            suggestions.add(val)
            
        # Check boccard_item_number
        val = str(row["boccard_item_number"] or "").strip()
        if query_lower in val.lower():
            suggestions.add(val)
            
        # Check extra_data values
        extra = json.loads(row["extra_data"] or "{}")
        for k, v in extra.items():
            val = str(v).strip()
            if query_lower in val.lower():
                suggestions.add(val)
                
    # Sort by how closely they match (starts with query > contains query)
    sorted_suggestions = sorted(list(suggestions), key=lambda x: (not x.lower().startswith(query_lower), x.lower()))
    
    # Filter out empty strings and return up to limit
    return [s for s in sorted_suggestions if s][:limit]


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


def get_setting(key, default=None):
    conn = _connect()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = _connect()
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?",
        (key, value, value)
    )
    conn.commit()
    conn.close()

def get_user_by_username(username):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = _connect()
    rows = conn.execute("SELECT id, username, email, role, status FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_user(username, email, password_hash, role='user', status='active'):
    conn = _connect()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash, role, status) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, role, status)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except Exception:
        user_id = None
    finally:
        conn.close()
    return user_id

def update_user_status(user_id, status):
    conn = _connect()
    conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = _connect()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_login_enabled():
    val = get_setting("login_enabled", "1")
    return val == "1"
