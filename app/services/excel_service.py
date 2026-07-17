import os
import re
from itertools import islice
from openpyxl import load_workbook


def _normalize_header(header):
    if header is None:
        return ""
    text = str(header).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _map_value(record, header, value):
    normalized = _normalize_header(header)
    if value is None:
        return

    text = str(value).strip()
    if not text:
        return

    is_pid_remarks = (
        normalized in {"remarks_in_pid", "remarks_in_pid_database", "remarks_pid", "database_remarks"}
        or (
            ("remark" in normalized or "remak" in normalized)
            and ("pid" in normalized or "p_id" in normalized or "database" in normalized)
        )
    )

    if is_pid_remarks:
        record["remarks_in_pid"] = text
    elif normalized in {"boccard_item_number", "boccard", "boccard_item", "item_number"} or "boccard" in normalized:
        record["boccard_item_number"] = text
    elif normalized in {"tag_number", "tag", "tag_no", "tagnumber"} or "tag" in normalized:
        record["tag_number"] = text
    elif normalized in {"designation", "design", "desig"} or "designation" in normalized:
        record["designation"] = text
    else:
        record["extra_data"][header] = text


def _score_header_row(row):
    score = 0
    for value in row:
        normalized = _normalize_header(value)
        if not normalized:
            continue

        if "remark" in normalized or "remak" in normalized or "pid" in normalized:
            score += 2
        if "boccard" in normalized or "item_number" in normalized:
            score += 2
        if normalized in {"tag", "tag_no", "tag_number", "tagnumber"} or "tag" in normalized:
            score += 2
        if "designation" in normalized:
            score += 2

    return score


def _find_header_index(rows):
    best_index = 0
    best_score = 0

    for index, row in enumerate(rows[:25]):
        score = _score_header_row(row)
        if score > best_score:
            best_index = index
            best_score = score

    return best_index


def _find_best_sheet(workbook):
    best_sheet = workbook.active
    best_header_index = 0
    best_score = 0

    for sheet in workbook.worksheets:
        sample_rows = list(islice(sheet.iter_rows(values_only=True), 25))
        if not sample_rows:
            continue

        header_index = _find_header_index(sample_rows)
        score = _score_header_row(sample_rows[header_index])
        if score > best_score:
            best_sheet = sheet
            best_header_index = header_index
            best_score = score

    rows = list(best_sheet.iter_rows(values_only=True))
    return best_sheet, rows, best_header_index


def parse_excel_file(path):
    workbook = load_workbook(path, data_only=True, read_only=True)
    _sheet, rows, header_index = _find_best_sheet(workbook)
    if not rows:
        return []

    headers = [str(header).strip() if header is not None else "" for header in rows[header_index]]
    parsed_rows = []

    for row in rows[header_index + 1:]:
        if not row or all(value is None or str(value).strip() == "" for value in row):
            continue

        record = {
            "remarks_in_pid": "",
            "boccard_item_number": "",
            "tag_number": "",
            "designation": "",
            "category": "Uncategorized",
            "extra_data": {},
        }

        for index, value in enumerate(row):
            if index >= len(headers):
                continue
            _map_value(record, headers[index], value)

        desig = str(record.get("designation", "")).lower()
        if "valve" in desig or "actuator" in desig:
            record["category"] = "Valves & Actuators"
        elif "pump" in desig:
            record["category"] = "Pumps"
        elif "pipe" in desig or "fitting" in desig or "flange" in desig:
            record["category"] = "Piping & Fittings"
        elif "tank" in desig or "vessel" in desig:
            record["category"] = "Tanks & Vessels"
        elif "sensor" in desig or "transmitter" in desig or "gauge" in desig or "meter" in desig or "indicator" in desig:
            record["category"] = "Instruments"
        elif "motor" in desig or "electrical" in desig:
            record["category"] = "Electrical"
        elif desig:
            record["category"] = "Other"

        parsed_rows.append(record)

    return parsed_rows
