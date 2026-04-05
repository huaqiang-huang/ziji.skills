#!/usr/bin/env python3
"""
个人微信本地探测器（实验）
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wechat_common import build_manifest, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="个人微信本地探测器（实验）")
    parser.add_argument("--platform", default="auto", help="auto | macos | windows")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="显式指定候选根目录，可重复传入",
    )
    parser.add_argument("--output", help="输出 JSON manifest 文件路径")
    args = parser.parse_args()

    explicit_roots = [Path(item).expanduser() for item in args.root] if args.root else None
    manifest = build_manifest(args.platform, explicit_roots)

    if args.output:
        write_json(Path(args.output).expanduser(), manifest)
        print(f"已写入 manifest：{args.output}")
        return

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
