#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WorkBuddy C 盘友好版 · 只读体检

一次看清：
  1) 各盘总容量 / 剩余 / 使用率，哪些是固定盘（junction 只能落在固定盘上）
  2) WorkBuddy 相关目录的真实体积，以及 ~/.workbuddy 是否已经是目录联接（junction）
  3) 运行态内部谁最占地方（Top N 子目录）
  4) 技能数 / 自动化条数 / 落在 C 盘的工作区
  5) 结论：要不要搬、搬多少能腾出来

设计约定：
  - 只读。不写任何被检查的目录，不启动程序，不改配置。
  - 遇到权限错误 / 文件被占用 / 目录消失，一律跳过并计数，不中断。
  - Windows 专用（依赖 kernel32 判断驱动器类型与重解析点）。

用法：
  python diagnose.py
  python diagnose.py --json
  python diagnose.py --no-size            # 跳过体积统计，秒出
  python diagnose.py --save baseline.json # 存一份基线
  python diagnose.py --compare baseline.json
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import os
import shutil
import sqlite3
import string
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # 老 Python / 重定向到文件
    pass

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
DRIVE_TYPES = {
    2: "REMOVABLE",
    3: "FIXED",
    4: "NETWORK",
    5: "CDROM",
    6: "RAMDISK",
}

HOME = os.path.expanduser("~")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
APPDATA = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")

_k32 = ctypes.windll.kernel32
_k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
_k32.GetFileAttributesW.restype = ctypes.c_uint32
_k32.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
_k32.GetDriveTypeW.restype = ctypes.c_uint32


# --------------------------------------------------------------------------- #
# 基础探测
# --------------------------------------------------------------------------- #
def is_reparse_point(path: str) -> bool:
    """判断是否为重解析点（junction / symlink）。注意：os.path.islink() 对 junction 返回 False。"""
    attrs = _k32.GetFileAttributesW(path)
    if attrs == 0xFFFFFFFF:  # INVALID_FILE_ATTRIBUTES
        return False
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def link_target(path: str):
    """返回联接指向的目标；不是联接则返回 None。"""
    try:
        return os.readlink(path)
    except (OSError, NotImplementedError, ValueError):
        return None


def human(n):
    if n is None:
        return "-"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def size_map(root: str):
    """单遍遍历，同时得到 (总体积, {一级子项名: 体积})。

    两件事一次做完，避免同一棵树走两遍（85k 文件时能省一半时间）。
    跳过内部联接，避免重复计算或绕进死循环。
    """
    total = 0
    per = {}
    stack = [(root, None)]
    while stack:
        cur, top = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_dir():
                            if is_reparse_point(entry.path):
                                continue  # 联接不跟随
                            sub = top if top is not None else entry.name
                            per.setdefault(sub, 0)
                            stack.append((entry.path, sub))
                        else:
                            sz = entry.stat(follow_symlinks=False).st_size
                            total += sz
                            if top is not None:
                                per[top] = per.get(top, 0) + sz
                    except OSError:
                        continue
        except OSError:
            continue
    return total, per


def dir_size(path: str):
    """只要总体积时的薄封装。"""
    return size_map(path)[0]


def drives():
    out = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        dtype = _k32.GetDriveTypeW(root)
        if dtype not in DRIVE_TYPES:
            continue
        if dtype not in (2, 3, 4):  # 只关心磁盘类
            continue
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        out.append(
            {
                "drive": f"{letter}:",
                "type": DRIVE_TYPES[dtype],
                "total": usage.total,
                "free": usage.free,
                "used": usage.used,
                "free_pct": round(usage.free / usage.total * 100, 1) if usage.total else 0.0,
            }
        )
    return out


def walk_depth(path: str, max_depth: int = 1):
    """列出指定深度内所有目录（不跟随联接）。备用工具，体检主流程已改用 size_map。"""
    out = []
    base = path.rstrip("\\/")
    for root, dirs, _files in os.walk(base):
        rel = os.path.relpath(root, base)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= max_depth:
            dirs[:] = []
            continue
        keep = []
        for d in dirs:
            full = os.path.join(root, d)
            if is_reparse_point(full):
                continue
            keep.append(d)
            out.append(full)
        dirs[:] = keep
    return out


# --------------------------------------------------------------------------- #
# WorkBuddy 专项
# --------------------------------------------------------------------------- #
def runtime_targets():
    return [
        ("运行态（主）", os.path.join(HOME, ".workbuddy"), True),
        ("Playwright 内核", os.path.join(LOCALAPPDATA, "ms-playwright"), True),
        ("WorkBuddy 应用数据", os.path.join(APPDATA, "WorkBuddy"), False),
        ("CodeBuddy 扩展", os.path.join(LOCALAPPDATA, "CodeBuddyExtension"), False),
        ("CodeBuddy 数据", os.path.join(HOME, ".codebuddy"), False),
        ("密钥回退目录", os.path.join(HOME, ".workbuddy-key-fallback"), False),
    ]


def runtime_info(do_size=True, top=10):
    main_path = os.path.join(HOME, ".workbuddy")
    main_size, main_per = (None, {})
    if do_size and os.path.isdir(main_path):
        main_size, main_per = size_map(main_path)  # 主目录只走一遍

    items = []
    for label, path, primary in runtime_targets():
        if not os.path.exists(path):
            continue
        if do_size:
            size = main_size if os.path.normcase(path) == os.path.normcase(main_path) else dir_size(path)
        else:
            size = None
        items.append(
            {
                "label": label,
                "path": path,
                "primary": primary,
                "exists": True,
                "junction": is_reparse_point(path),
                "target": link_target(path),
                "real": os.path.realpath(path),
                "size": size,
            }
        )

    top_dirs = []
    if main_per:
        sized = [{"name": k, "size": v} for k, v in main_per.items()]
        sized.sort(key=lambda x: x["size"], reverse=True)
        top_dirs = sized[:top]

    return items, top_dirs


def db_info():
    db = os.path.join(HOME, ".workbuddy", "workbuddy.db")
    info = {"path": db, "exists": os.path.exists(db), "automations": None, "workspaces": []}
    if not info["exists"]:
        return info
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        info["error"] = "数据库被占用，无法只读打开（程序运行时偶发）"
        return info
    try:
        cur = con.cursor()
        try:
            info["automations"] = cur.execute(
                "select count(*) from automations where deleted_at is null"
            ).fetchone()[0]
        except sqlite3.Error:
            pass
        try:
            for path, last in cur.execute("select path, last_opened_at from workspaces"):
                info["workspaces"].append({"path": path, "last_opened_at": last})
        except sqlite3.Error:
            pass
    finally:
        con.close()
    return info


def skills_count():
    root = os.path.join(HOME, ".workbuddy", "skills")
    if not os.path.isdir(root):
        return 0
    n = 0
    for name in os.listdir(root):
        if os.path.isfile(os.path.join(root, name, "SKILL.md")):
            n += 1
    return n


def snapshot(do_size=True):
    items, top = runtime_info(do_size=do_size)
    db = db_info()
    main = next((i for i in items if i["primary"]), None)
    return {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "drives": drives(),
        "runtime": items,
        "runtime_top": top,
        "skills": skills_count(),
        "automations": db.get("automations"),
        "workspaces": db.get("workspaces"),
        "db_path": db["path"],
        "_main": main,
    }


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def print_report(snap):
    print("=" * 78)
    print(" WorkBuddy C 盘友好版 · 只读体检   " + snap["generated_at"])
    print("=" * 78)

    print("\n[1] 磁盘")
    print(f"  {'盘':<4}{'类型':<11}{'总量':>10}{'剩余':>10}{'使用率':>9}")
    for d in snap["drives"]:
        print(
            f"  {d['drive']:<4}{d['type']:<11}{human(d['total']):>10}"
            f"{human(d['free']):>10}{100 - d['free_pct']:>8.0f}%"
        )

    print("\n[2] WorkBuddy 相关目录（C 盘占用候选）")
    total = 0
    for item in snap["runtime"]:
        mark = ""
        if item["junction"]:
            mark = "  [已是联接]"
        if item["size"]:
            total += item["size"]
        print(f"  {item['label']:<20}{human(item['size']) if item['size'] is not None else '-':>10}  {item['path']}{mark}")
        if item["junction"]:
            print(f"  {'':<20}{'':>10}  -> {item['real']}")
    print(f"  {'合计':<20}{human(total):>10}")

    if snap["runtime_top"]:
        print("\n[3] 运行态内部 Top 占用")
        for d in snap["runtime_top"]:
            print(f"  {human(d['size']):>10}  {d['name']}")

    print("\n[4] 资产")
    print(f"  技能（含 SKILL.md）: {snap['skills']}")
    print(f"  自动化（未删除）    : {snap['automations'] if snap['automations'] is not None else '-'}")
    print(f"  登记工作区          : {len(snap['workspaces'] or [])}")

    on_c = []
    missing = []
    for ws in snap["workspaces"] or []:
        p = ws["path"]
        if not os.path.isdir(p):
            missing.append(p)
        elif p[:2].upper() == "C:":
            on_c.append(p)
    if on_c:
        print("\n  [!] 工作空间根在 C 盘（建议迁出）：")
        for p in on_c:
            print(f"      {p}")
    if missing:
        print("\n  [!] 工作区路径已不存在（自动化会静默不跑）：")
        for p in missing:
            print(f"      {p}")

    # 结论
    print("\n[5] 结论")
    main = snap["_main"]
    c = next((d for d in snap["drives"] if d["drive"] == "C:"), None)
    if main and main["junction"]:
        print(f"  [OK] 运行态已搬出 C 盘：{main['path']}")
        print(f"       -> {main['real']}")
        print("       写法仍用 C 盘路径；资源管理器里体积显示很小是正常的。")
    elif main:
        print(f"  [!!] 运行态仍在 C 盘：{main['path']}（{human(main['size'])}）")

    if c:
        if c["free"] < 5 * 1024**3 or c["free_pct"] < 15:
            print(
                f"  [!!] C: 剩余 {human(c['free'])}（{c['free_pct']}%）"
                "—— 低于 5 GB / 15% 阈值，建议处理"
            )
        else:
            print(f"  [OK] C: 剩余 {human(c['free'])}（{c['free_pct']}%）")

    movable = sum(i["size"] or 0 for i in snap["runtime"] if i["primary"] and not i["junction"])
    if movable:
        print(f"  [>>] 可将 {human(movable)} 搬到非系统盘（原路径不变，可回滚）")
        print("       下一步：python make_bat.py --pair \"<源>::<目标>\" --exe WorkBuddy.exe --out <目录>")
    elif main and main["junction"]:
        print("  [>>] 可搬的主项已经搬完。若 C 盘仍紧，按 references/decision.md 做全网盘盘点。")


def print_compare(base, now):
    print("=" * 78)
    print(" 基线对比（迁移前 vs 现在）")
    print("=" * 78)
    print(f"  基线时间: {base.get('generated_at')}")
    print(f"  当前时间: {now.get('generated_at')}")

    def line(label, a, b):
        same = a == b
        print(f"  {'OK ' if same else '!! '}{label:<16}{str(a):>22}{str(b):>22}")

    print(f"\n  {'':<3}{'项':<14}{'基线':>22}{'当前':>22}")
    line("技能数", base.get("skills"), now.get("skills"))
    line("自动化条数", base.get("automations"), now.get("automations"))
    line("工作区数", len(base.get("workspaces") or []), len(now.get("workspaces") or []))

    bm = base.get("_main") or {}
    nm = now.get("_main") or {}
    line("运行态体积", human(bm.get("size")), human(nm.get("size")))
    print(f"  {'OK ' if nm.get('junction') else '!! '}联接状态      "
          f"{'junction' if bm.get('junction') else 'real':>22}{'junction' if nm.get('junction') else 'real':>22}")
    if nm.get("junction"):
        print(f"      现在指向: {nm.get('real')}")

    print("\n  磁盘剩余变化:")
    bd = {d["drive"]: d for d in base.get("drives", [])}
    for d in now.get("drives", []):
        old = bd.get(d["drive"])
        if not old:
            continue
        delta = d["free"] - old["free"]
        if abs(delta) < 1024 * 1024:
            change = "  ="
        else:
            change = ("  +" if delta > 0 else "  -") + human(abs(delta))
        print(f"    {d['drive']}  {human(old['free']):>10} -> {human(d['free']):>10}{change}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="WorkBuddy C 盘友好版 · 只读体检")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--no-size", action="store_true", help="跳过体积统计")
    ap.add_argument("--top", type=int, default=10, help="运行态 Top N 子目录")
    ap.add_argument("--save", metavar="FILE", help="保存基线 JSON")
    ap.add_argument("--compare", metavar="FILE", help="与基线 JSON 对比")
    args = ap.parse_args(argv)

    if sys.platform != "win32":
        print("[ERROR] 本脚本只支持 Windows（依赖 kernel32 判断驱动器类型与重解析点）")
        return 2

    do_size = not args.no_size
    snap = snapshot(do_size=do_size)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        print(f"[OK] 基线已保存: {args.save}")

    if args.compare:
        try:
            with open(args.compare, encoding="utf-8") as f:
                base = json.load(f)
        except (OSError, ValueError) as e:
            print(f"[ERROR] 读取基线失败: {e}")
            return 1
        print_compare(base, snap)
        return 0

    if args.json:
        out = {k: v for k, v in snap.items() if k != "_main"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print_report(snap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
