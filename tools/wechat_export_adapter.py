#!/usr/bin/env python3
"""
微信导出适配器（实验）
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from wechat_common import WECHAT_MESSAGE_FIELDS, content_preview, normalize_timestamp, write_json


JSON_ALIAS_MAP = {
    "account_id": ["account_id", "wxid", "user", "owner"],
    "conversation_id": ["conversation_id", "talker", "chat_id", "room_id", "session_id"],
    "conversation_name": ["conversation_name", "chat_name", "room_name", "nickname", "session_name"],
    "sender": ["sender", "sender_name", "from", "from_user", "username"],
    "timestamp": ["timestamp", "create_time", "time", "msg_time", "datetime"],
    "msg_type": ["msg_type", "type", "message_type"],
    "content_text": ["content_text", "content", "text", "message", "body", "msg"],
}
LINE_PATTERN = re.compile(
    r"^(?P<time>\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]\d{1,2}:\d{2}(?::\d{2})?)\s+(?P<sender>.+?)[:：]\s*(?P<content>.+)$"
)


def detect_format(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    lower_name = path.name.lower()
    if "wechatmsg" in lower_name:
        return "wechatmsg"
    if "pywxdump" in lower_name:
        return "pywxdump"
    if "留痕" in path.name:
        return "liuhen"
    return "generic"


def normalize_record(source_file: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    normalized = dict.fromkeys(WECHAT_MESSAGE_FIELDS, "")
    for field, aliases in JSON_ALIAS_MAP.items():
        for alias in aliases:
            if alias in row and row[alias] not in (None, ""):
                normalized[field] = str(row[alias]).strip()
                break

    if not normalized["content_text"]:
        return None

    normalized["content_preview"] = content_preview(normalized["content_text"])
    normalized["timestamp"] = normalize_timestamp(normalized["timestamp"])
    normalized["attachments"] = []
    normalized["source_db"] = str(source_file)
    normalized["decode_status"] = "decoded"
    normalized["sender_role"] = row.get("sender_role", "unknown") or "unknown"
    return normalized


def parse_json_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("messages") or payload.get("records") or payload.get("data") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    return [record for row in rows if isinstance(row, dict) for record in [normalize_record(path, row)] if record]


def parse_csv_file(path: Path) -> list[dict[str, Any]]:
    results = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            record = normalize_record(path, row)
            if record:
                results.append(record)
    return results


def parse_txt_file(path: Path) -> list[dict[str, Any]]:
    results = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        matched = LINE_PATTERN.match(line.strip())
        if not matched:
            continue
        record = normalize_record(
            path,
            {
                "timestamp": matched.group("time"),
                "sender": matched.group("sender"),
                "content_text": matched.group("content"),
            },
        )
        if record:
            results.append(record)
    return results


def collect_input_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file() and child.suffix.lower() in {".json", ".csv", ".txt"}:
            files.append(child)
    return files


def collect_attachments(path: Path) -> list[dict[str, Any]]:
    items = []
    for child in sorted(path.rglob("*")) if path.is_dir() else []:
        if not child.is_file():
            continue
        if child.suffix.lower() in {".json", ".csv", ".txt"}:
            continue
        items.append({
            "path": str(child),
            "name": child.name,
            "size": child.stat().st_size,
        })
    return items


def dedupe_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    results = []
    for item in messages:
        key = (
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


def format_messages_txt(messages: list[dict[str, Any]]) -> str:
    lines = ["# 微信导出适配结果", ""]
    for message in messages:
        timestamp = message.get("timestamp") or "unknown-time"
        sender = message.get("sender") or "unknown-sender"
        lines.append(f"[{timestamp}] {sender}: {message.get('content_text', '')}")
    if len(lines) == 2:
        lines.append("（未匹配到可识别的导出消息）")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="微信导出适配器（实验）")
    parser.add_argument("--input", required=True, help="导出文件或导出目录")
    parser.add_argument("--format", default="auto", help="auto | liuhen | wechatmsg | pywxdump | generic")
    parser.add_argument("--output-dir", required=True, help="标准化输出目录")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    detected_format = detect_format(input_path, args.format)
    messages: list[dict[str, Any]] = []
    parsed_files = []

    for source_file in collect_input_files(input_path):
        suffix = source_file.suffix.lower()
        if suffix == ".json":
            parsed = parse_json_file(source_file)
        elif suffix == ".csv":
            parsed = parse_csv_file(source_file)
        else:
            parsed = parse_txt_file(source_file)
        messages.extend(parsed)
        parsed_files.append(str(source_file))

    messages = dedupe_messages(messages)
    attachments = collect_attachments(input_path)

    write_json(output_dir / "messages.json", messages)
    (output_dir / "messages.txt").write_text(format_messages_txt(messages), encoding="utf-8")
    write_json(output_dir / "attachments_manifest.json", attachments)
    write_json(
        output_dir / "parse_report.json",
        {
            "detected_format": detected_format,
            "input": str(input_path),
            "parsed_files": parsed_files,
            "messages_extracted": len(messages),
            "notes": [
                "当前版本优先做统一格式适配，不依赖某一个导出工具的固定 schema。",
            ],
        },
    )
    print(f"已输出到 {output_dir}")


if __name__ == "__main__":
    main()
