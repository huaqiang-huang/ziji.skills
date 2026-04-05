#!/usr/bin/env python3
"""
自己.skill 版本管理器

负责 self skill 的备份、列版本、回滚和清理。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_VERSIONS = 10
TRACKED_FILES = [
    "SKILL.md",
    "meta.json",
    "work.md",
    "persona.md",
    "principles.md",
    "recovery.md",
    "work_skill.md",
    "persona_skill.md",
    "principles_skill.md",
    "recovery_skill.md",
]


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def list_versions(skill_dir: Path) -> list[dict]:
    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        return []

    versions = []
    for version_dir in sorted(versions_dir.iterdir(), key=lambda p: p.stat().st_mtime):
        if not version_dir.is_dir():
            continue
        archived_at = datetime.fromtimestamp(
            version_dir.stat().st_mtime,
            tz=timezone.utc,
        ).strftime("%Y-%m-%d %H:%M")
        files = [f.name for f in version_dir.iterdir() if f.is_file()]
        versions.append({
            "version": version_dir.name,
            "archived_at": archived_at,
            "files": sorted(files),
            "path": str(version_dir),
        })
    return versions


def backup(skill_dir: Path, name: str | None = None) -> str:
    meta_path = skill_dir / "meta.json"
    version_hint = "manual"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        version_hint = str(meta.get("version", "manual"))

    backup_name = name or f"{version_hint}_backup_{now_stamp()}"
    backup_dir = skill_dir / "versions" / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    for filename in TRACKED_FILES:
        src = skill_dir / filename
        if src.exists():
            shutil.copy2(src, backup_dir / filename)

    return backup_name


def rollback(skill_dir: Path, target_version: str) -> bool:
    version_dir = skill_dir / "versions" / target_version
    if not version_dir.exists():
        print(f"错误：版本 {target_version} 不存在", file=sys.stderr)
        return False

    backup_name = backup(skill_dir, name=f"pre_rollback_{now_stamp()}")
    restored_files = []
    for filename in TRACKED_FILES:
        src = version_dir / filename
        if src.exists():
            shutil.copy2(src, skill_dir / filename)
            restored_files.append(filename)

    meta_path = skill_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["version"] = f"{target_version}_restored"
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta["rollback_from_backup"] = backup_name
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已回滚到 {target_version}，恢复文件：{', '.join(restored_files)}")
    return True


def cleanup_old_versions(skill_dir: Path, max_versions: int = MAX_VERSIONS) -> None:
    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        return

    version_dirs = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    to_delete = version_dirs[:-max_versions] if len(version_dirs) > max_versions else []
    for old_dir in to_delete:
        shutil.rmtree(old_dir)
        print(f"已清理旧版本：{old_dir.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="自己.skill 版本管理器")
    parser.add_argument("--action", required=True, choices=["list", "backup", "rollback", "cleanup"])
    parser.add_argument("--slug", required=True, help="self slug")
    parser.add_argument("--version", help="目标版本号（rollback 时使用）")
    parser.add_argument("--name", help="备份名称（backup 时可选）")
    parser.add_argument(
        "--base-dir",
        default="./selves",
        help="self skill 根目录",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()
    skill_dir = base_dir / args.slug

    if not skill_dir.exists():
        print(f"错误：找不到 self skill 目录 {skill_dir}", file=sys.stderr)
        sys.exit(1)

    if args.action == "list":
        versions = list_versions(skill_dir)
        if not versions:
            print(f"{args.slug} 暂无历史版本")
        else:
            print(f"{args.slug} 的历史版本：\n")
            for item in versions:
                print(
                    f"  {item['version']}  存档时间: {item['archived_at']}  "
                    f"文件: {', '.join(item['files'])}"
                )
        return

    if args.action == "backup":
        created = backup(skill_dir, args.name)
        print(f"已创建备份：{created}")
        return

    if args.action == "rollback":
        if not args.version:
            print("错误：rollback 操作需要 --version", file=sys.stderr)
            sys.exit(1)
        rollback(skill_dir, args.version)
        return

    cleanup_old_versions(skill_dir)
    print("清理完成")


if __name__ == "__main__":
    main()
