#!/usr/bin/env python3
"""
自己.skill 文件写入器

负责将四层内容写入到正确的目录结构，
并生成 meta.json、完整 SKILL.md、以及四个子 skill 文件。

用法：
    python3 skill_writer.py --action create --name "青云" --meta meta.json \
        --work work.md --persona persona.md --principles principles.md --recovery recovery.md \
        --base-dir ./selves

    python3 skill_writer.py --action update --slug qing-yun \
        --work-patch work_patch.md --persona-patch persona_patch.md \
        --principles-patch principles_patch.md --recovery-patch recovery_patch.md \
        --base-dir ./selves

    python3 skill_writer.py --action list --base-dir ./selves
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


LAYER_FILES = {
    "work": "work.md",
    "persona": "persona.md",
    "principles": "principles.md",
    "recovery": "recovery.md",
}

SUBSKILL_FILES = {
    "work": "work_skill.md",
    "persona": "persona_skill.md",
    "principles": "principles_skill.md",
    "recovery": "recovery_skill.md",
}

LAYER_TITLES = {
    "work": "Work",
    "persona": "Persona",
    "principles": "Principles",
    "recovery": "Recovery",
}

DEFAULT_MODE = "best"
LIST_FIELDS = ("slug", "name", "mode", "version", "updated_at", "corrections_count")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_text(path: Optional[str]) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8").strip()


def slugify(name: str) -> str:
    """
    统一使用 kebab-case。
    中文优先尝试转拼音，英文/数字保留并转为小写。
    """
    if not name:
        return "self"

    try:
        from pypinyin import lazy_pinyin

        converted = []
        for chunk in lazy_pinyin(name, errors="ignore"):
            chunk = re.sub(r"[^a-zA-Z0-9]+", "-", chunk.lower())
            if chunk:
                converted.append(chunk)
        slug = "-".join(part for part in converted if part)
    except ImportError:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower())

    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "self"


def build_identity_string(meta: dict[str, Any]) -> str:
    profile = meta.get("profile", {})
    parts = []

    company = str(profile.get("company", "")).strip()
    level = str(profile.get("level", "")).strip()
    role = str(profile.get("role", "")).strip()
    mbti = str(profile.get("mbti", "")).strip()

    for value in (company, level, role):
        if value:
            parts.append(value)

    identity = " ".join(parts) if parts else "Self Skill"
    if mbti:
        identity = f"{identity}，MBTI {mbti}"
    return identity


def normalize_runtime_targets(meta: dict[str, Any]) -> list[str]:
    targets = meta.get("runtime_targets")
    if not isinstance(targets, list):
        return ["claude", "openclaw", "codex"]

    normalized = []
    for item in targets:
        value = str(item).strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    return normalized or ["claude", "openclaw", "codex"]


def normalize_sources(meta: dict[str, Any]) -> list[dict[str, Any]]:
    sources = meta.get("sources")
    if not isinstance(sources, list):
        return []

    normalized = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        normalized.append({
            "type": str(source.get("type", "unknown")).strip() or "unknown",
            "path_or_origin": str(source.get("path_or_origin", "")).strip(),
            "weight": str(source.get("weight", "medium")).strip() or "medium",
            "imported_at": str(source.get("imported_at", now_iso())).strip() or now_iso(),
        })
    return normalized


def ensure_meta_defaults(meta: dict[str, Any], slug: str) -> dict[str, Any]:
    meta = dict(meta)
    now = now_iso()

    meta["slug"] = slug
    meta["mode"] = str(meta.get("mode", DEFAULT_MODE)).strip() or DEFAULT_MODE
    meta.setdefault("created_at", now)
    meta["updated_at"] = now
    meta.setdefault("version", "v1")
    meta.setdefault("profile", {})
    meta.setdefault("self_definition", "")
    meta.setdefault("traits_to_keep", [])
    meta.setdefault("traits_to_fix", [])
    meta["sources"] = normalize_sources(meta)
    meta["runtime_targets"] = normalize_runtime_targets(meta)
    meta.setdefault("corrections_count", 0)
    meta.setdefault("idealization_notes", [])
    return meta


def strip_leading_h1(content: str) -> str:
    content = content.strip()
    lines = content.splitlines()
    if not lines:
        return ""
    if lines[0].lstrip().startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def compose_main_skill(meta: dict[str, Any], sections: dict[str, str]) -> str:
    slug = meta["slug"]
    name = meta.get("name", slug)
    identity = build_identity_string(meta)
    mode = meta.get("mode", DEFAULT_MODE)

    merged_sections = {
        layer: strip_leading_h1(text)
        for layer, text in sections.items()
    }

    return f"""---
name: self-{slug}
description: {name}，{identity}
user-invocable: true
---

# {name}

{identity}

当前模式：`{mode}`

---

## Principles

{merged_sections["principles"]}

---

## Persona

{merged_sections["persona"]}

---

## Work

{merged_sections["work"]}

---

## Recovery

{merged_sections["recovery"]}

---

## 运行规则

接收到任何任务或问题时：

1. 先遵守用户当前指令。
2. 如存在 correction，以 correction 为准。
3. 再按 Principles 做判断和取舍。
4. 如遇阻、信息不足或冲突，按 Recovery 换路和自检。
5. 输出时保持 Persona 的表达风格。
6. 执行时按 Work 的方法和规范落地。
"""


def compose_subskill(meta: dict[str, Any], layer: str, content: str) -> str:
    slug = meta["slug"]
    name = meta.get("name", slug)
    title = LAYER_TITLES[layer]
    return f"""---
name: self-{slug}-{layer}
description: {name} 的 {title} 层
user-invocable: true
---

{content}
"""


def write_skill_files(skill_dir: Path, meta: dict[str, Any], sections: dict[str, str]) -> None:
    for layer, filename in LAYER_FILES.items():
        (skill_dir / filename).write_text(sections[layer].strip() + "\n", encoding="utf-8")

    (skill_dir / "SKILL.md").write_text(compose_main_skill(meta, sections), encoding="utf-8")

    for layer, filename in SUBSKILL_FILES.items():
        (skill_dir / filename).write_text(
            compose_subskill(meta, layer, sections[layer]),
            encoding="utf-8",
        )

    (skill_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def snapshot_current_version(skill_dir: Path, version_name: str) -> Path:
    version_dir = skill_dir / "versions" / version_name
    version_dir.mkdir(parents=True, exist_ok=True)

    tracked = [
        "SKILL.md",
        "meta.json",
        *LAYER_FILES.values(),
        *SUBSKILL_FILES.values(),
    ]
    for filename in tracked:
        src = skill_dir / filename
        if src.exists():
            shutil.copy2(src, version_dir / filename)

    return version_dir


def next_version_name(current_version: str) -> str:
    match = re.search(r"v(\d+)", current_version or "")
    if not match:
        return "v2"
    return f"v{int(match.group(1)) + 1}"


def append_patch(existing: str, patch: str) -> str:
    existing = existing.rstrip()
    patch = patch.strip()
    if not patch:
        return existing
    if not existing:
        return patch
    return f"{existing}\n\n{patch}"


def apply_correction(existing: str, correction: dict[str, Any]) -> str:
    line = correction.get("line")
    if not line:
        scene = correction.get("scene", "通用")
        wrong = correction.get("wrong", "")
        correct = correction.get("correct", "")
        note = correction.get("note", "")
        line = f"- [场景：{scene}] 不应该 {wrong}，应该 {correct}"
        if note:
            line += f"（备注：{note}）"

    target = "## Correction 记录"
    if target in existing:
        insert_pos = existing.index(target) + len(target)
        rest = existing[insert_pos:]
        skip = "\n\n（暂无记录）"
        if rest.startswith(skip):
            rest = rest[len(skip):]
        return existing[:insert_pos] + "\n" + line + rest

    return existing.rstrip() + f"\n\n## Correction 记录\n{line}\n"


def create_skill(
    base_dir: Path,
    slug: str,
    meta: dict[str, Any],
    sections: dict[str, str],
) -> Path:
    skill_dir = base_dir / slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    (skill_dir / "versions").mkdir(exist_ok=True)
    (skill_dir / "knowledge" / "docs").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "messages").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "emails").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "code").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "notes").mkdir(parents=True, exist_ok=True)

    meta = ensure_meta_defaults(meta, slug)
    write_skill_files(skill_dir, meta, sections)
    snapshot_current_version(skill_dir, meta["version"])
    return skill_dir


def update_skill(
    skill_dir: Path,
    patches: dict[str, str],
    correction: Optional[dict[str, Any]] = None,
) -> str:
    meta_path = skill_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    current_version = str(meta.get("version", "v1"))
    snapshot_current_version(skill_dir, current_version)

    sections: dict[str, str] = {}
    for layer, filename in LAYER_FILES.items():
        sections[layer] = (skill_dir / filename).read_text(encoding="utf-8").rstrip()

    for layer, patch in patches.items():
        if patch:
            sections[layer] = append_patch(sections[layer], patch)

    if correction:
        target_layer = str(correction.get("layer", "persona")).strip().lower()
        if target_layer not in sections:
            raise ValueError(f"unknown correction layer: {target_layer}")
        sections[target_layer] = apply_correction(sections[target_layer], correction)
        meta["corrections_count"] = int(meta.get("corrections_count", 0)) + 1

    meta["version"] = next_version_name(current_version)
    meta["updated_at"] = now_iso()

    write_skill_files(skill_dir, meta, sections)
    snapshot_current_version(skill_dir, meta["version"])
    return meta["version"]


def list_selves(base_dir: Path) -> list[dict[str, Any]]:
    selves = []
    if not base_dir.exists():
        return selves

    for skill_dir in sorted(base_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        meta_path = skill_dir / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        selves.append({
            "slug": meta.get("slug", skill_dir.name),
            "name": meta.get("name", skill_dir.name),
            "mode": meta.get("mode", DEFAULT_MODE),
            "version": meta.get("version", "v1"),
            "updated_at": meta.get("updated_at", ""),
            "corrections_count": meta.get("corrections_count", 0),
        })

    return selves


def delete_skill(base_dir: Path, slug: str) -> Path:
    skill_dir = base_dir / slug
    if not skill_dir.exists():
        raise FileNotFoundError(f"找不到 self skill 目录 {skill_dir}")
    shutil.rmtree(skill_dir)
    return skill_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="自己.skill 文件写入器")
    parser.add_argument("--action", required=True, choices=["create", "update", "list", "delete"])
    parser.add_argument("--slug", help="self slug（kebab-case）")
    parser.add_argument("--name", help="self name")
    parser.add_argument("--meta", help="meta.json 文件路径")
    parser.add_argument("--work", help="work.md 内容文件路径")
    parser.add_argument("--persona", help="persona.md 内容文件路径")
    parser.add_argument("--principles", help="principles.md 内容文件路径")
    parser.add_argument("--recovery", help="recovery.md 内容文件路径")
    parser.add_argument("--work-patch", help="work.md 增量更新内容文件路径")
    parser.add_argument("--persona-patch", help="persona.md 增量更新内容文件路径")
    parser.add_argument("--principles-patch", help="principles.md 增量更新内容文件路径")
    parser.add_argument("--recovery-patch", help="recovery.md 增量更新内容文件路径")
    parser.add_argument("--correction", help="correction json 文件路径")
    parser.add_argument(
        "--base-dir",
        default="./selves",
        help="self Skill 根目录（默认：./selves）",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()

    if args.action == "list":
        selves = list_selves(base_dir)
        if not selves:
            print("暂无已创建的 self skill")
        else:
            print(f"已创建 {len(selves)} 个 self skill：\n")
            for item in selves:
                values = [str(item.get(field, "")) for field in LIST_FIELDS]
                print(" | ".join(values))
        return

    if args.action == "delete":
        if not args.slug:
            print("错误：delete 操作需要 --slug", file=sys.stderr)
            sys.exit(1)
        deleted = delete_skill(base_dir, args.slug)
        print(f"✅ 已删除 self skill：{deleted}")
        return

    meta: dict[str, Any] = {}
    if args.meta:
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    if args.name:
        meta["name"] = args.name

    if args.action == "create":
        if not args.slug and not meta.get("name"):
            print("错误：create 操作需要 --slug 或 --name", file=sys.stderr)
            sys.exit(1)
        slug = args.slug or str(meta.get("slug", "")).strip() or slugify(meta.get("name", "self"))
        sections = {
            "work": load_text(args.work),
            "persona": load_text(args.persona),
            "principles": load_text(args.principles),
            "recovery": load_text(args.recovery),
        }
        skill_dir = create_skill(base_dir, slug, meta, sections)
        print(f"✅ self skill 已创建：{skill_dir}")
        print(f"   触发词：/self-{slug}")
        return

    if not args.slug:
        print("错误：update 操作需要 --slug", file=sys.stderr)
        sys.exit(1)

    slug = args.slug
    skill_dir = base_dir / slug
    if not skill_dir.exists():
        print(f"错误：找不到 self skill 目录 {skill_dir}", file=sys.stderr)
        sys.exit(1)

    patches = {
        "work": load_text(args.work_patch),
        "persona": load_text(args.persona_patch),
        "principles": load_text(args.principles_patch),
        "recovery": load_text(args.recovery_patch),
    }
    correction = None
    if args.correction:
        correction = json.loads(Path(args.correction).read_text(encoding="utf-8"))

    new_version = update_skill(skill_dir, patches, correction)
    print(f"✅ self skill 已更新到 {new_version}：{skill_dir}")


if __name__ == "__main__":
    main()
