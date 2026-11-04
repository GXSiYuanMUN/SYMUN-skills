#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验仓库内所有 Skill 是否符合 Agent Skills 开放标准。

依据: https://openagentskills.dev/docs/specification

检查项:
  1. 目录名合法（小写字母/数字/连字符，不以连字符开头结尾，无连续连字符，<=64 字符）
  2. SKILL.md 存在
  3. frontmatter 为合法 YAML，含 name 与 description
  4. name 合法（1-64 字符，小写字母/数字/连字符）
  5. name 与父目录名完全一致
  6. description 非空且 <=1024 字符
  7. license 若声明，则仓库内存在对应文件
  8. references/ 下的文件为一级（不嵌套子目录链）
  9. SKILL.md 正文引用的 references/scripts 文件确实存在

退出码: 0 = 全部通过 ; 1 = 存在不合规项
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC = 1024

errors = []
warnings = []


def fail(skill: str, msg: str):
    errors.append(f"[{skill}] {msg}")


def warn(skill: str, msg: str):
    warnings.append(f"[{skill}] {msg}")


def parse_frontmatter(text: str):
    """极简 YAML frontmatter 解析：只处理 key: value 与 key: | 块。"""
    if not text.startswith("---"):
        return None, None, "文件未以 '---' 开头，缺少 frontmatter"
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not m:
        return None, None, "frontmatter 格式不合法（缺少结束的 ---）"
    raw = m.group(1)
    body = text[m.end():]

    data = {}
    key = None
    block = []
    for line in raw.splitlines():
        if key and (line.startswith("  ") or line.startswith("\t") or not line.strip()):
            block.append(line.strip())
            continue
        if key:
            data[key] = " ".join(x for x in block if x).strip()
            key, block = None, []
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            k, v = km.group(1), km.group(2).strip()
            if v in ("|", ">", "|-", ">-"):
                key = k
                block = []
            else:
                data[k] = v.strip().strip('"').strip("'")
    if key:
        data[key] = " ".join(x for x in block if x).strip()
    return data, body, None


def validate_skill(skill_dir: Path):
    name = skill_dir.name

    # 1. 目录名
    if len(name) > MAX_NAME:
        fail(name, f"目录名超过 {MAX_NAME} 字符")
    if not NAME_RE.match(name):
        fail(name, f"目录名 '{name}' 不合法：只允许小写字母、数字和连字符，且不以连字符开头/结尾，不含连续连字符")

    # 2. SKILL.md 存在
    md = skill_dir / "SKILL.md"
    if not md.exists():
        fail(name, "缺少 SKILL.md")
        return
    text = md.read_text(encoding="utf-8")

    # 3. frontmatter
    data, body, err = parse_frontmatter(text)
    if err:
        fail(name, err)
        return
    if not data.get("name"):
        fail(name, "frontmatter 缺少 name 字段")
    if not data.get("description"):
        fail(name, "frontmatter 缺少 description 字段")

    # 4. name 合法
    sname = data.get("name", "")
    if len(sname) > MAX_NAME:
        fail(name, f"name 超过 {MAX_NAME} 字符")
    if not NAME_RE.match(sname):
        fail(name, f"name '{sname}' 不合法：只允许小写字母、数字和连字符")

    # 5. name == 目录名
    if sname and sname != name:
        fail(name, f"name 字段 '{sname}' 与父目录名 '{name}' 不一致（规范要求完全一致）")

    # 6. description 长度
    desc = data.get("description", "")
    if len(desc) > MAX_DESC:
        fail(name, f"description 超过 {MAX_DESC} 字符（当前 {len(desc)}）")
    if desc and "使用" not in desc and "Use when" not in desc and "当用户" not in desc:
        warn(name, "description 未包含明确的触发条件描述")

    # 7. license 对应文件存在
    lic = data.get("license", "")
    if lic:
        candidates = [
            skill_dir / lic,
            skill_dir / "LICENSE.txt",
            skill_dir / "LICENSE",
            ROOT / lic,
            ROOT / "LICENSE",
        ]
        if not any(c.exists() for c in candidates):
            fail(name, f"声明了 license '{lic}'，但仓库内找不到对应文件")

    # 8. references 不应嵌套子目录
    refs = skill_dir / "references"
    if refs.exists():
        for sub in refs.rglob("*"):
            if sub.is_dir():
                warn(name, f"references/ 存在嵌套目录 '{sub.relative_to(skill_dir)}'（规范建议只用一级）")

    # 9. SKILL.md 中引用的相对路径文件是否存在
    #    只匹配形如 `references/xxx.md` 或 `scripts/xxx.py` 的纯路径引用，
    #    排除代码块内容与含空格/占位符的行
    for m in re.finditer(r"`((?:references|scripts|assets)/[^`\s]+)`", body):
        rel = m.group(1).strip()
        if any(ch in rel for ch in "*?"):
            continue
        if not (skill_dir / rel).exists():
            fail(name, f"SKILL.md 引用了不存在的文件：{rel}")


def main():
    skill_dirs = sorted(
        p for p in SKILLS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in ("scripts", "tests", "assets")
    )

    if not skill_dirs:
        print("未发现任何 Skill 目录", file=sys.stderr)
        return 1

    print(f"发现 {len(skill_dirs)} 个 Skill 目录，开始校验…\n")
    for d in skill_dirs:
        print(f"  · {d.name}")
        validate_skill(d)

    print()
    if warnings:
        print("── 警告 ──")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if errors:
        print("── 错误 ──")
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n校验未通过：{len(errors)} 项错误，{len(warnings)} 项警告")
        return 1

    print(f"✓ 全部通过：{len(skill_dirs)} 个 Skill，{len(warnings)} 项警告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
