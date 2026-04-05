#!/usr/bin/env python3
"""
自己.skill 最小冒烟测试

在临时目录中覆盖：
- create
- list
- update
- correction
- backup
- rollback
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_writer = repo_root / "tools" / "skill_writer.py"
    version_manager = repo_root / "tools" / "version_manager.py"
    validator = repo_root / "tools" / "validate_self_skill.py"
    examples_dir = repo_root / "examples"

    with tempfile.TemporaryDirectory(prefix="self_skill_smoke_") as temp_dir:
        temp_root = Path(temp_dir)
        base_dir = temp_root / "selves"
        base_dir.mkdir(parents=True, exist_ok=True)

        meta_path = temp_root / "meta.json"
        work_patch_path = temp_root / "work_patch.md"
        correction_path = temp_root / "correction.json"

        write_json(
            meta_path,
            {
                "name": "Test Self",
                "mode": "best",
                "profile": {
                    "company": "Self Lab",
                    "level": "Owner",
                    "role": "Workflow Builder",
                },
                "self_definition": "A compact smoke-test profile.",
                "traits_to_keep": ["结论前置", "先做最小验证", "交付带验证"],
                "traits_to_fix": ["任务多时过载", "解释不够", "偶尔贪快"],
                "sources": [
                    {
                        "type": "manual",
                        "path_or_origin": "smoke test",
                        "weight": "medium",
                        "imported_at": "2026-04-05T00:00:00+00:00",
                    }
                ],
                "runtime_targets": ["claude", "openclaw", "codex"],
                "idealization_notes": ["Keep the profile execution-oriented."],
            },
        )
        work_patch_path.write_text("\n- 新增：更新后会同步检查组合 skill。\n", encoding="utf-8")
        write_json(
            correction_path,
            {
                "layer": "principles",
                "scene": "需求不清时",
                "wrong": "直接开写",
                "correct": "先收敛目标再实现",
            },
        )

        run(
            [
                "python3",
                str(skill_writer),
                "--action",
                "create",
                "--meta",
                str(meta_path),
                "--work",
                str(examples_dir / "sample_work.md"),
                "--persona",
                str(examples_dir / "sample_persona.md"),
                "--principles",
                str(examples_dir / "sample_principles.md"),
                "--recovery",
                str(examples_dir / "sample_recovery.md"),
                "--base-dir",
                str(base_dir),
            ],
            repo_root,
        )

        skill_dir = base_dir / "test-self"
        assert skill_dir.exists(), "create 未生成 test-self 目录"
        assert "## Principles" in (skill_dir / "SKILL.md").read_text(encoding="utf-8")

        list_result = run(
            [
                "python3",
                str(skill_writer),
                "--action",
                "list",
                "--base-dir",
                str(base_dir),
            ],
            repo_root,
        )
        assert "test-self | Test Self | best | v1" in list_result.stdout

        run(
            [
                "python3",
                str(skill_writer),
                "--action",
                "update",
                "--slug",
                "test-self",
                "--work-patch",
                str(work_patch_path),
                "--correction",
                str(correction_path),
                "--base-dir",
                str(base_dir),
            ],
            repo_root,
        )

        updated_meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
        assert updated_meta["version"] == "v2"
        assert updated_meta["corrections_count"] == 1
        assert "\n## Principles\n\n## 1. 核心原则" in (skill_dir / "SKILL.md").read_text(encoding="utf-8")

        backup_result = run(
            [
                "python3",
                str(version_manager),
                "--action",
                "backup",
                "--slug",
                "test-self",
                "--base-dir",
                str(base_dir),
            ],
            repo_root,
        )
        assert "已创建备份" in backup_result.stdout

        run(
            [
                "python3",
                str(version_manager),
                "--action",
                "rollback",
                "--slug",
                "test-self",
                "--version",
                "v1",
                "--base-dir",
                str(base_dir),
            ],
            repo_root,
        )

        rolled_back_meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
        assert rolled_back_meta["version"].startswith("v1_restored")
        assert rolled_back_meta["corrections_count"] == 0

        run(
            [
                "python3",
                str(validator),
                "--repo-root",
                str(repo_root),
                "--base-dir",
                str(base_dir),
                "--examples-generated-dir",
                str(temp_root / "generated_examples"),
            ],
            repo_root,
        )

        print("smoke test passed")


if __name__ == "__main__":
    main()
