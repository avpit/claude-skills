#!/usr/bin/env python3
"""Convert Claude Code SKILL.md files into Cursor AI .mdc project rules.

Usage:
    scripts/skill_to_cursor_rule.py                          # convert every skills/*/SKILL.md
    scripts/skill_to_cursor_rule.py skills/git-workflow/SKILL.md
    scripts/skill_to_cursor_rule.py --out .cursor/rules skills/git-workflow/SKILL.md

Cursor project rules live under .cursor/rules/<name>.mdc with their own
frontmatter (description, globs, alwaysApply). This maps a SKILL.md's
name/description frontmatter onto that shape and carries the body over
unchanged, emitting an "Agent Requested" rule (alwaysApply: false, no globs)
-- the closest Cursor equivalent to Claude Code loading a skill on demand
based on its description.
"""
import argparse
import pathlib
import re
import sys

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)", re.DOTALL)


def parse_skill(path: pathlib.Path) -> tuple[str, str, str]:
    text = path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter found")
    frontmatter, body = m.group(1), m.group(2)

    name_m = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    desc_m = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_m or not desc_m:
        raise ValueError(f"{path}: frontmatter missing name or description")

    return name_m.group(1).strip(), desc_m.group(1).strip(), body.strip()


def to_cursor_rule(description: str, body: str) -> str:
    desc_block = "\n".join("  " + line for line in description.splitlines())
    return (
        "---\n"
        f"description: >-\n{desc_block}\n"
        "globs:\n"
        "alwaysApply: false\n"
        "---\n\n"
        f"{body}\n"
    )


def convert(skill_path: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    name, description, body = parse_skill(skill_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.mdc"
    out_path.write_text(to_cursor_rule(description, body))
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skill_md",
        nargs="*",
        type=pathlib.Path,
        help="Path(s) to SKILL.md files. Defaults to every skills/*/SKILL.md.",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=pathlib.Path(".cursor/rules"),
        help="Output directory for .mdc files (default: .cursor/rules)",
    )
    args = parser.parse_args()

    targets = args.skill_md or sorted(pathlib.Path("skills").glob("*/SKILL.md"))
    if not targets:
        print("No SKILL.md files found.", file=sys.stderr)
        return 1

    for skill_path in targets:
        try:
            out_path = convert(skill_path, args.out)
        except ValueError as e:
            print(f"skip {skill_path}: {e}", file=sys.stderr)
            continue
        print(f"{skill_path} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
