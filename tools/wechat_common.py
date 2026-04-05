#!/usr/bin/env python3
"""
微信实验工具共享能力
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACCOUNT_DIR_PATTERN = re.compile(r"^(wxid_[a-zA-Z0-9]+)(?:_[a-zA-Z0-9]+)?$")
DB_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".fts"}
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".tsv", ".log"}
WECHAT_MESSAGE_FIELDS = [
    "account_id",
    "conversation_id",
    "conversation_name",
    "sender",
    "sender_role",
    "timestamp",
    "msg_type",
    "content_text",
    "content_preview",
    "attachments",
    "source_db",
    "decode_status",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_platform(platform: str) -> str:
    value = (platform or "auto").strip().lower()
    if value == "auto":
        if os.name == "nt":
            return "windows"
        return "macos"
    if value in {"mac", "darwin"}:
        return "macos"
    if value in {"win", "win32"}:
        return "windows"
    return value


def default_roots(platform: str) -> list[Path]:
    home = Path.home()
    if platform == "macos":
        return [
            home / "Library" / "Containers" / "com.tencent.xinWeChat" / "Data" / "Documents",
            home / "Library" / "Group Containers" / "5A4RE8SF68.com.tencent.xinWeChat",
        ]

    if platform == "windows":
        roots: list[Path] = []
        user_profile = os.environ.get("USERPROFILE")
        appdata = os.environ.get("APPDATA")
        local_appdata = os.environ.get("LOCALAPPDATA")
        if user_profile:
            roots.append(Path(user_profile) / "Documents" / "WeChat Files")
        if appdata:
            roots.append(Path(appdata) / "Tencent" / "WeChat")
        if local_appdata:
            roots.append(Path(local_appdata) / "Tencent" / "WeChat")
        return roots

    return []


def file_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def is_account_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if path.name == "all_users":
        return False
    return bool(ACCOUNT_DIR_PATTERN.match(path.name))


def account_id_from_dir(path: Path) -> str:
    match = ACCOUNT_DIR_PATTERN.match(path.name)
    if match:
        return match.group(1)
    return path.name


def classify_db_file(path: Path) -> str:
    name = path.name.lower()
    parts = [part.lower() for part in path.parts]
    if "message" in name or "message" in parts:
        return "message"
    if "session" in name or "session" in parts:
        return "session"
    if "contact" in name or "contact" in parts:
        return "contact"
    if "media" in name or "resource" in name:
        return "media"
    if "biz" in name:
        return "biz"
    return "other"


def discover_account_dirs(root: Path, platform: str) -> list[Path]:
    results: list[Path] = []

    if platform == "macos":
        candidates = [
            root / "xwechat_files",
            root,
        ]
        for base in candidates:
            if not base.exists():
                continue
            for child in sorted(base.iterdir()):
                if is_account_dir(child):
                    results.append(child)
        return dedupe_paths(results)

    if platform == "windows":
        for child in sorted(root.iterdir()) if root.exists() else []:
            if is_account_dir(child):
                results.append(child)
            elif child.is_dir() and child.name.lower() == "wechat files":
                for nested in sorted(child.iterdir()):
                    if is_account_dir(nested):
                        results.append(nested)
        return dedupe_paths(results)

    return []


def find_db_files(account_dir: Path) -> list[dict[str, Any]]:
    db_files: list[dict[str, Any]] = []
    for path in sorted(account_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in DB_SUFFIXES:
            continue
        item = file_info(path)
        item["kind"] = classify_db_file(path)
        db_files.append(item)
    return db_files


def find_attachment_dirs(account_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for relative in [
        Path("msg"),
        Path("msg") / "attach",
        Path("msg") / "file",
        Path("msg") / "video",
        Path("msg") / "voice",
        Path("msg") / "image",
        Path("media"),
    ]:
        target = account_dir / relative
        if target.exists() and target.is_dir():
            item = file_info(target)
            item["path"] = str(target)
            candidates.append(item)
    return candidates


def discover_account(account_dir: Path) -> dict[str, Any]:
    return {
        "account_id": account_id_from_dir(account_dir),
        "account_dir": str(account_dir),
        "db_files": find_db_files(account_dir),
        "attachment_dirs": find_attachment_dirs(account_dir),
    }


def build_manifest(platform: str, explicit_roots: list[Path] | None = None) -> dict[str, Any]:
    platform = normalize_platform(platform)
    roots = explicit_roots or default_roots(platform)
    manifest_roots = []
    accounts: list[dict[str, Any]] = []

    for root in roots:
        root = root.expanduser().resolve()
        root_entry: dict[str, Any] = {
            "path": str(root),
            "exists": root.exists(),
            "accounts_found": 0,
        }
        if root.exists():
            found_accounts = [discover_account(path) for path in discover_account_dirs(root, platform)]
            root_entry["accounts_found"] = len(found_accounts)
            accounts.extend(found_accounts)
        manifest_roots.append(root_entry)

    return {
        "generated_at": now_iso(),
        "platform": platform,
        "roots": manifest_roots,
        "accounts": dedupe_accounts(accounts),
    }


def dedupe_paths(paths: list[Path]) -> list[Path]:
    seen = set()
    results = []
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        results.append(path)
    return results


def dedupe_accounts(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    results = []
    for account in accounts:
        key = account.get("account_dir")
        if key in seen:
            continue
        seen.add(key)
        results.append(account)
    return results


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def content_preview(text: str, limit: int = 120) -> str:
    value = (text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def normalize_timestamp(value: Any) -> str:
    if value in (None, ""):
        return ""

    as_int = safe_int(value)
    if as_int is not None:
        if as_int > 10**14:
            as_int = as_int // 1000
        elif as_int > 10**11:
            as_int = as_int // 1000
        try:
            return datetime.fromtimestamp(as_int, tz=timezone.utc).isoformat()
        except Exception:
            pass
    return str(value)


def list_media_files(directory: Path, limit: int = 300) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not directory.exists():
        return items
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        items.append(file_info(path))
        if len(items) >= limit:
            break
    return items


def guess_sender_role(sender: str, account_id: str) -> str:
    sender_value = (sender or "").strip()
    if not sender_value:
        return "unknown"
    if sender_value == account_id:
        return "self"
    return "other"

