#!/usr/bin/env python3
"""
微信实验总入口
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="微信实验总入口")
    parser.add_argument("--mode", required=True, choices=["probe", "parse", "adapt", "local"])
    parser.add_argument("--platform", default="auto", help="auto | macos | windows")
    parser.add_argument("--root", action="append", default=[], help="显式指定微信候选根目录，可重复传入")
    parser.add_argument("--manifest", help="现有 manifest 文件")
    parser.add_argument("--input", help="导出文件或导出目录（adapt 模式使用）")
    parser.add_argument("--format", default="auto", help="auto | liuhen | wechatmsg | pywxdump | generic")
    parser.add_argument("--output-dir", help="标准化输出目录")
    parser.add_argument("--output", help="probe 输出路径")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    tools_dir = repo_root / "tools"
    probe = tools_dir / "wechat_local_probe.py"
    parser_tool = tools_dir / "wechat_local_parser.py"
    adapter = tools_dir / "wechat_export_adapter.py"

    if args.mode == "probe":
        command = ["python3", str(probe), "--platform", args.platform]
        for root in args.root:
            command.extend(["--root", root])
        if args.output:
            command.extend(["--output", args.output])
        run(command)
        return

    if args.mode == "parse":
        if not args.output_dir:
            raise SystemExit("错误：parse 模式需要 --output-dir")
        command = ["python3", str(parser_tool), "--output-dir", args.output_dir]
        if args.manifest:
            command.extend(["--manifest", args.manifest])
        elif args.root:
            command.extend(["--root", args.root[0], "--platform", args.platform])
        else:
            raise SystemExit("错误：parse 模式需要 --manifest 或 --root")
        run(command)
        return

    if args.mode == "adapt":
        if not args.input or not args.output_dir:
            raise SystemExit("错误：adapt 模式需要 --input 和 --output-dir")
        run([
            "python3",
            str(adapter),
            "--input",
            args.input,
            "--format",
            args.format,
            "--output-dir",
            args.output_dir,
        ])
        return

    if not args.output_dir:
        raise SystemExit("错误：local 模式需要 --output-dir")

    manifest_path = args.manifest or str(repo_root / "examples" / "wechat" / "manifest.auto.json")
    probe_command = ["python3", str(probe), "--platform", args.platform, "--output", manifest_path]
    for root in args.root:
        probe_command.extend(["--root", root])
    run(probe_command)
    run([
        "python3",
        str(parser_tool),
        "--manifest",
        manifest_path,
        "--output-dir",
        args.output_dir,
    ])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
