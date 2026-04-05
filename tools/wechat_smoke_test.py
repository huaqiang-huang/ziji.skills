#!/usr/bin/env python3
"""
微信实验能力冒烟测试
"""

from __future__ import annotations

import csv
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def create_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE message_records (
            conversation_id TEXT,
            conversation_name TEXT,
            sender TEXT,
            msg_type TEXT,
            content_text TEXT,
            timestamp INTEGER
        )
        """
    )
    conn.execute(
        """
        INSERT INTO message_records VALUES
        ('chat-1', '测试群', 'alice', 'text', '第一条测试消息', 1712275200),
        ('chat-1', '测试群', 'bob', 'text', '第二条测试消息', 1712275260)
        """
    )
    conn.commit()
    conn.close()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    probe = repo_root / "tools" / "wechat_local_probe.py"
    parser = repo_root / "tools" / "wechat_local_parser.py"
    adapter = repo_root / "tools" / "wechat_export_adapter.py"

    with tempfile.TemporaryDirectory(prefix="wechat_smoke_") as temp_dir:
        temp_root = Path(temp_dir)
        mac_root = temp_root / "Documents"
        account_dir = mac_root / "xwechat_files" / "wxid_testuser_1234"
        db_dir = account_dir / "db_storage" / "message"
        attach_dir = account_dir / "msg" / "attach"
        export_dir = temp_root / "exports"
        output_dir = temp_root / "out"
        adapter_out = temp_root / "adapter_out"
        manifest_path = temp_root / "manifest.json"

        db_dir.mkdir(parents=True, exist_ok=True)
        attach_dir.mkdir(parents=True, exist_ok=True)
        export_dir.mkdir(parents=True, exist_ok=True)
        (attach_dir / "demo.bin").write_bytes(b"demo-attachment")
        create_sqlite(db_dir / "message_0.db")

        json.dump(
            [
                {
                    "conversation_id": "chat-json",
                    "conversation_name": "JSON 会话",
                    "sender": "json-user",
                    "timestamp": 1712275300,
                    "content_text": "json 消息",
                }
            ],
            (export_dir / "messages.json").open("w", encoding="utf-8"),
            ensure_ascii=False,
        )
        with (export_dir / "messages.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["sender", "timestamp", "content_text"])
            writer.writeheader()
            writer.writerow({"sender": "csv-user", "timestamp": 1712275400, "content_text": "csv 消息"})
        (export_dir / "messages.txt").write_text("2024-04-05 12:00:00 txt-user: txt 消息\n", encoding="utf-8")

        run(
            ["python3", str(probe), "--platform", "macos", "--root", str(mac_root), "--output", str(manifest_path)],
            repo_root,
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["accounts"], "probe 未发现测试账号目录"

        run(
            ["python3", str(parser), "--manifest", str(manifest_path), "--output-dir", str(output_dir)],
            repo_root,
        )
        parsed_messages = json.loads((output_dir / "messages.json").read_text(encoding="utf-8"))
        assert len(parsed_messages) >= 2, "local parser 未解析出样例消息"
        assert (output_dir / "attachments_manifest.json").exists()

        run(
            ["python3", str(adapter), "--input", str(export_dir), "--format", "auto", "--output-dir", str(adapter_out)],
            repo_root,
        )
        adapted_messages = json.loads((adapter_out / "messages.json").read_text(encoding="utf-8"))
        assert len(adapted_messages) >= 3, "export adapter 未解析出样例导出消息"

        print("wechat smoke test passed")


if __name__ == "__main__":
    main()
