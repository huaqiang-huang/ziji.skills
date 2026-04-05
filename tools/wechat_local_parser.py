#!/usr/bin/env python3
"""
个人微信本地解析器（实验）
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from wechat_common import (
    WECHAT_MESSAGE_FIELDS,
    build_manifest,
    classify_db_file,
    content_preview,
    guess_sender_role,
    list_media_files,
    normalize_timestamp,
    write_json,
)

ROW_LIMIT_PER_TABLE = 500
MESSAGE_COLUMN_ALIASES = {
    "conversation_id": {"conversation_id", "talker", "strtalker", "session_id", "chat_id", "roomid"},
    "conversation_name": {"conversation_name", "display_name", "chat_name", "nickname", "room_name"},
    "sender": {"sender", "sender_id", "from_user", "fromuser", "des", "talker", "username"},
    "timestamp": {"timestamp", "create_time", "createtime", "msgtime", "time", "sortseq"},
    "msg_type": {"msg_type", "msgtype", "type", "message_type"},
    "content_text": {"content", "content_text", "plaintext", "text", "digest", "description", "summary", "title"},
}


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_db(source_path: Path, temp_dir: Path) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    destination = temp_dir / source_path.name
    shutil.copy2(source_path, destination)
    return destination


def sqlite_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def fetch_tables(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def fetch_columns(conn: sqlite3.Connection, table_name: str) -> list[dict[str, Any]]:
    cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "default_value": row[4],
            "pk": row[5],
        }
        for row in cursor.fetchall()
    ]


def candidate_message_tables(tables: list[str], db_kind: str) -> list[str]:
    preferred = []
    for table in tables:
        lower = table.lower()
        if lower.startswith("sqlite_"):
            continue
        if "message" in lower or "msg" in lower or db_kind == "message":
            preferred.append(table)
        elif db_kind in {"session", "contact"} and any(token in lower for token in ("session", "contact", "chat")):
            preferred.append(table)
    if preferred:
        return preferred
    return [table for table in tables if not table.lower().startswith("sqlite_")]


def choose_column(columns: list[str], alias_name: str) -> str:
    aliases = MESSAGE_COLUMN_ALIASES[alias_name]
    for column in columns:
        if column.lower() in aliases:
            return column
    return ""


def normalize_row(
    account_id: str,
    table_name: str,
    db_path: Path,
    column_names: list[str],
    row_values: tuple[Any, ...],
) -> dict[str, Any] | None:
    row = dict(zip(column_names, row_values))
    conversation_id_col = choose_column(column_names, "conversation_id")
    conversation_name_col = choose_column(column_names, "conversation_name")
    sender_col = choose_column(column_names, "sender")
    timestamp_col = choose_column(column_names, "timestamp")
    msg_type_col = choose_column(column_names, "msg_type")
    content_col = choose_column(column_names, "content_text")

    text_candidates = []
    for key, value in row.items():
        if isinstance(value, (bytes, bytearray)):
            continue
        if value is None:
            continue
        if isinstance(value, (int, float)):
            continue
        value_str = str(value).strip()
        if not value_str:
            continue
        text_candidates.append((key, value_str))

    content_text_value = ""
    if content_col:
        value = row.get(content_col)
        if value not in (None, "") and not isinstance(value, (bytes, bytearray)):
            content_text_value = str(value).strip()

    if not content_text_value and text_candidates:
        content_text_value = max(text_candidates, key=lambda item: len(item[1]))[1]

    if not content_text_value:
        return None

    sender_value = str(row.get(sender_col, "")).strip() if sender_col else ""
    conversation_id_value = str(row.get(conversation_id_col, "")).strip() if conversation_id_col else ""
    conversation_name_value = str(row.get(conversation_name_col, "")).strip() if conversation_name_col else ""

    normalized = dict.fromkeys(WECHAT_MESSAGE_FIELDS, "")
    normalized.update({
        "account_id": account_id,
        "conversation_id": conversation_id_value,
        "conversation_name": conversation_name_value,
        "sender": sender_value,
        "sender_role": guess_sender_role(sender_value, account_id),
        "timestamp": normalize_timestamp(row.get(timestamp_col, "")) if timestamp_col else "",
        "msg_type": str(row.get(msg_type_col, "")).strip() if msg_type_col else table_name,
        "content_text": content_text_value,
        "content_preview": content_preview(content_text_value),
        "attachments": [],
        "source_db": str(db_path),
        "decode_status": "decoded",
    })
    return normalized


def parse_database(account_id: str, source_db_path: Path, temp_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    db_report: dict[str, Any] = {
        "db_path": str(source_db_path),
        "db_kind": classify_db_file(source_db_path),
        "status": "pending",
        "tables": [],
        "errors": [],
        "messages_extracted": 0,
    }
    copied_db = copy_db(source_db_path, temp_dir)

    try:
        conn = sqlite_connection(copied_db)
    except Exception as exc:
        db_report["status"] = "unreadable"
        db_report["errors"].append(str(exc))
        return [], db_report

    try:
        try:
            tables = fetch_tables(conn)
        except Exception as exc:
            db_report["status"] = "unreadable"
            db_report["errors"].append(str(exc))
            return [], db_report

        db_report["tables"] = tables
        candidates = candidate_message_tables(tables, db_report["db_kind"])
        messages: list[dict[str, Any]] = []

        for table_name in candidates:
            try:
                columns = fetch_columns(conn, table_name)
                column_names = [column["name"] for column in columns]
                cursor = conn.execute(f"SELECT * FROM '{table_name}' LIMIT {ROW_LIMIT_PER_TABLE}")
                for row in cursor.fetchall():
                    normalized = normalize_row(account_id, table_name, source_db_path, column_names, row)
                    if normalized:
                        messages.append(normalized)
            except Exception as exc:
                db_report["errors"].append(f"{table_name}: {exc}")

        db_report["messages_extracted"] = len(messages)
        db_report["status"] = "decoded" if messages else "opened_no_messages"
        return messages, db_report
    finally:
        conn.close()


def attachments_manifest(account: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for directory in account.get("attachment_dirs", []):
        items.extend(list_media_files(Path(directory["path"])))
    return items


def format_messages_txt(messages: list[dict[str, Any]]) -> str:
    lines = ["# 微信本地解析结果", ""]
    for message in messages:
        timestamp = f"[{message['timestamp']}]" if message.get("timestamp") else "[unknown-time]"
        sender = message.get("sender") or "unknown-sender"
        conversation = message.get("conversation_name") or message.get("conversation_id") or "unknown-conversation"
        lines.append(f"{timestamp} {conversation} {sender}: {message.get('content_text', '')}")
    if len(lines) == 2:
        lines.append("（未解析出正文，可查看 parse_report.json）")
    return "\n".join(lines) + "\n"


def dedupe_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    results = []
    for item in messages:
        key = (
            item.get("account_id"),
            item.get("conversation_id"),
            item.get("sender"),
            item.get("timestamp"),
            item.get("content_text"),
            item.get("source_db"),
        )
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="个人微信本地解析器（实验）")
    parser.add_argument("--manifest", help="probe 生成的 manifest JSON")
    parser.add_argument("--root", help="显式指定一个微信候选根目录")
    parser.add_argument("--platform", default="auto", help="auto | macos | windows")
    parser.add_argument("--output-dir", required=True, help="标准化输出目录")
    args = parser.parse_args()

    if not args.manifest and not args.root:
        raise SystemExit("错误：需要 --manifest 或 --root")

    manifest = (
        load_manifest(Path(args.manifest).expanduser())
        if args.manifest
        else build_manifest(args.platform, [Path(args.root).expanduser()])
    )

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    messages: list[dict[str, Any]] = []
    db_reports: list[dict[str, Any]] = []
    attachment_items: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="wechat_local_parser_") as temp_dir:
        temp_path = Path(temp_dir)
        for account in manifest.get("accounts", []):
            account_id = account["account_id"]
            attachment_items.extend(attachments_manifest(account))
            for db_item in account.get("db_files", []):
                parsed_messages, db_report = parse_database(account_id, Path(db_item["path"]), temp_path / account_id)
                messages.extend(parsed_messages)
                db_reports.append(db_report)

    messages = dedupe_messages(messages)
    parse_report = {
        "generated_at": manifest.get("generated_at"),
        "platform": manifest.get("platform"),
        "accounts_found": len(manifest.get("accounts", [])),
        "messages_extracted": len(messages),
        "db_reports": db_reports,
        "notes": [
            "如果 db_report.status 为 unreadable，通常意味着数据库经过加密或当前版本结构不可直接读取。",
            "此工具不会修改任何微信原目录，只会复制库到临时目录后尝试解析。",
        ],
    }

    write_json(output_dir / "messages.json", messages)
    (output_dir / "messages.txt").write_text(format_messages_txt(messages), encoding="utf-8")
    write_json(output_dir / "attachments_manifest.json", attachment_items)
    write_json(output_dir / "parse_report.json", parse_report)
    print(f"已输出到 {output_dir}")


if __name__ == "__main__":
    main()
