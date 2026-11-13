#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""枚举 WorkBuddy 自动化：定义 / 绑定工作区 / 运行档案位置（只读）。

为什么需要它：
  WorkBuddy 的自动化定义存在运行态目录的 SQLite（workbuddy.db）里，
  但每条自动化都用 cwds[0] **绑定到一个工作区**。
  当你打开的工作区不是它的 cwd 时，界面上就看不到它 —— 容易误以为"任务丢了"。
  本脚本直接把"谁绑在哪、档案在不在"打出来，用于寻址与体检。

用法：
  python list_automations.py                  # 人类可读表格
  python list_automations.py --json           # 机器可读
  python list_automations.py --cwd "E:\\my-workspace"   # 只列某个工作区的
  python list_automations.py --db <path>      # 指定 db（默认 ~/.workbuddy/workbuddy.db）

注意：
  - 只读打开数据库，不会修改任何东西。
  - 运行态目录可能是目录联接（junction），~/.workbuddy 会自动穿透，无需特殊处理。
"""
import argparse
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def default_db():
    return os.path.join(os.path.expanduser("~"), ".workbuddy", "workbuddy.db")


def open_ro(db_path):
    """只读打开。若因 WAL / 锁失败，退化为"复制一份再读"。"""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.execute("select 1 from automations limit 1")
        return con, db_path
    except sqlite3.Error:
        tmp = os.path.join(tempfile.mkdtemp(prefix="wbauto-"), "workbuddy.db")
        shutil.copy2(db_path, tmp)
        for suffix in ("-wal", "-shm"):
            if os.path.exists(db_path + suffix):
                shutil.copy2(db_path + suffix, tmp + suffix)
        con = sqlite3.connect(tmp)
        return con, tmp


def ts(ms):
    if not ms:
        return "-"
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, TypeError):
        return "-"


def human(ms):
    """把下次运行时间描述成相对天数。"""
    if not ms:
        return ""
    try:
        delta = datetime.datetime.fromtimestamp(ms / 1000) - datetime.datetime.now()
        d = delta.days
        if d < 0:
            return "(已过期)"
        return f"({d} 天后)" if d else "(今天)"
    except (OSError, ValueError, TypeError):
        return ""


def collect(con):
    con.row_factory = sqlite3.Row
    rows = []
    for r in con.execute(
        "select id, name, status, schedule_type, rrule, scheduled_at, cwds, "
        "workspace_scope, owner_status, next_run_at, last_run_at, created_at "
        "from automations where deleted_at is null order by created_at"
    ):
        d = dict(r)
        try:
            cwd_list = json.loads(d.get("cwds") or "[]")
        except (ValueError, TypeError):
            cwd_list = []
        cwd = cwd_list[0] if cwd_list else ""
        archive = os.path.join(cwd, ".workbuddy", "automations", d["id"]) if cwd else ""
        d["cwd"] = cwd
        d["archive_dir"] = archive
        d["archive_exists"] = bool(archive) and os.path.isdir(archive)
        d["archive_memory"] = os.path.join(archive, "memory.md") if archive else ""
        d["cwd_exists"] = bool(cwd) and os.path.isdir(cwd)
        rows.append(d)
    return rows


def main():
    ap = argparse.ArgumentParser(description="枚举 WorkBuddy 自动化及其工作区绑定")
    ap.add_argument("--db", default=default_db(), help="workbuddy.db 路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--cwd", help="只显示绑定到该工作区的自动化")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"[ERROR] 找不到数据库: {args.db}", file=sys.stderr)
        return 1

    con, used = open_ro(args.db)
    rows = collect(con)
    con.close()

    if args.cwd:
        key = os.path.normcase(os.path.normpath(args.cwd))
        rows = [r for r in rows if os.path.normcase(os.path.normpath(r["cwd"])) == key]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print(f"数据库    : {used}")
    print(f"运行态目录: {os.path.dirname(os.path.abspath(args.db))}")
    real = os.path.realpath(os.path.dirname(os.path.abspath(args.db)))
    if os.path.normcase(real) != os.path.normcase(os.path.dirname(os.path.abspath(args.db))):
        print(f"            (目录联接 → {real})")
    print()

    by_cwd = {}
    for r in rows:
        by_cwd.setdefault(r["cwd"], []).append(r)

    for cwd, items in by_cwd.items():
        flag = "" if os.path.isdir(cwd) else "   <<< 工作目录已不存在！"
        print(f"▼ 工作区: {cwd}{flag}")
        for r in items:
            mark = "OK " if r["archive_exists"] else "!! "
            when = r["scheduled_at"] if r["schedule_type"] == "once" else r["rrule"]
            print(
                f"  {mark}{r['id']:<40} {r['name'][:24]:<26} {r['status']:<7}"
                f" scope={r['workspace_scope'] or '-':<10} owner={r['owner_status'] or '-':<18}"
            )
            print(f"      计划: {when}   档案: {'有' if r['archive_exists'] else '缺'}  {r['archive_dir']}")
        print()

    n_ok = sum(1 for r in rows if r["archive_exists"])
    n_bad = len(rows) - n_ok
    n_missing_cwd = len({r["cwd"] for r in rows if r["cwd"] and not os.path.isdir(r["cwd"])})
    print(f"合计 {len(rows)} 条自动化，分布 {len(by_cwd)} 个工作区")
    print(f"档案在位 {n_ok} 条，档案缺失 {n_bad} 条，工作目录不存在 {n_missing_cwd} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
