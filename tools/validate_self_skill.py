#!/usr/bin/env python3
"""
自己.skill 只读校验器

检查：
- 仓库关键结构是否存在
- 生成产物目录是否完整
- meta.json 必填字段是否齐全
- 组合版 SKILL.md 顺序和标题拼装是否正确
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_ROOT_FILES = [
    "README.md",
    "SKILL.md",
    "INSTALL.md",
    "PROMPT迁移说明.md",
    "requirements.txt",
]

REQUIRED_ROOT_DIRS = [
    "prompts",
    "tools",
    "runtimes",
    "examples",
    "selves",
]

REQUIRED_SKILL_FILES = [
    "work.md",
    "persona.md",
    "principles.md",
    "recovery.md",
    "SKILL.md",
    "meta.json",
    "work_skill.md",
    "persona_skill.md",
    "principles_skill.md",
    "recovery_skill.md",
]

REQUIRED_META_FIELDS = [
    "name",
    "slug",
    "mode",
    "created_at",
    "updated_at",
    "version",
    "profile",
    "self_definition",
    "traits_to_keep",
    "traits_to_fix",
    "sources",
    "runtime_targets",
    "corrections_count",
    "idealization_notes",
]

SECTION_SEQUENCE = [
    "## Principles",
    "## Persona",
    "## Work",
    "## Recovery",
]


def validate_root(repo_root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_ROOT_FILES:
        path = repo_root / relative
        if not path.exists():
            errors.append(f"缺少仓库文件：{path}")
    for relative in REQUIRED_ROOT_DIRS:
        path = repo_root / relative
        if not path.exists():
            errors.append(f"缺少仓库目录：{path}")


def validate_meta(meta_path: Path, errors: list[str]) -> dict:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"无法解析 meta.json：{meta_path} ({exc})")
        return {}

    for field in REQUIRED_META_FIELDS:
        if field not in meta:
            errors.append(f"meta.json 缺少字段 {field}：{meta_path}")
    return meta


def validate_main_skill(skill_path: Path, errors: list[str]) -> None:
    text = skill_path.read_text(encoding="utf-8")
    positions = []
    for marker in SECTION_SEQUENCE:
        index = text.find(marker)
        if index == -1:
            errors.append(f"组合 SKILL.md 缺少章节 {marker}：{skill_path}")
            return
        positions.append(index)

    if positions != sorted(positions):
        errors.append(f"组合 SKILL.md 章节顺序错误：{skill_path}")

    for marker in SECTION_SEQUENCE:
        pattern = re.escape(marker) + r"\n\s*\n# "
        if re.search(pattern, text):
            errors.append(f"组合 SKILL.md 仍然嵌套了分层 H1：{skill_path}")


def validate_skill_dir(skill_dir: Path, errors: list[str]) -> None:
    for filename in REQUIRED_SKILL_FILES:
        path = skill_dir / filename
        if not path.exists():
            errors.append(f"缺少生成文件：{path}")
            continue
        if path.is_file() and path.stat().st_size == 0:
            errors.append(f"生成文件为空：{path}")

    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        errors.append(f"缺少 versions 目录：{versions_dir}")

    meta = validate_meta(skill_dir / "meta.json", errors)
    if meta:
        expected_slug = str(meta.get("slug", "")).strip()
        if expected_slug and skill_dir.name != expected_slug:
            errors.append(f"目录名与 slug 不一致：{skill_dir} vs {expected_slug}")

    validate_main_skill(skill_dir / "SKILL.md", errors)


def iter_skill_dirs(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return sorted(
        [path for path in base_dir.iterdir() if path.is_dir()],
        key=lambda path: path.name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="自己.skill 只读校验器")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="仓库根目录",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="待校验的 selves 目录，默认使用 {repo-root}/selves",
    )
    parser.add_argument(
        "--examples-generated-dir",
        default=None,
        help="生成样例目录，默认使用 {repo-root}/examples/generated",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    base_dir = Path(args.base_dir).expanduser().resolve() if args.base_dir else repo_root / "selves"
    examples_generated_dir = (
        Path(args.examples_generated_dir).expanduser().resolve()
        if args.examples_generated_dir
        else repo_root / "examples" / "generated"
    )

    errors: list[str] = []
    validate_root(repo_root, errors)

    checked = 0
    for skill_dir in iter_skill_dirs(base_dir):
        validate_skill_dir(skill_dir, errors)
        checked += 1

    for sample_dir in iter_skill_dirs(examples_generated_dir):
        validate_skill_dir(sample_dir, errors)
        checked += 1

    if errors:
        print("校验失败：", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        sys.exit(1)

    print(f"校验通过：已检查 {checked} 个 self 产物目录")


if __name__ == "__main__":
    main()
