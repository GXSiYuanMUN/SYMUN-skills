#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WorkBuddy C 盘友好版 · 生成迁移四件套（bat）+ 中文操作说明

为什么不让人手写 .bat：
  - 路径要逐个填、漏一个就搬一半
  - 编码必须是系统 ANSI 且行尾必须是 CRLF，手打极易踩坑
  - 失败回滚逻辑最容易写漏，而它恰恰是最关键的部分

本脚本按你给的 --pair 参数，生成：
  1_copy.bat      第一遍全量复制（程序可照常运行）
  2_cutover.bat   增量同步 -> 原目录改名 -> 建目录联接 -> 逐个校验；失败自动回滚
  3_cleanup.bat   删除 C 盘旧副本（要求手输 YES，且先校验联接在位）
  9_rollback.bat  删联接 -> 原名改回（目标盘数据不动）
  操作说明.md      给你的中文步骤说明

安全约定：
  - 生成的脚本只「复制 / 改名 / 建链接 / 删链接」，唯一删数据的是 3_cleanup.bat
  - 不改任何现有文件；只往 --out 指定目录写这 5 个文件

用法：
  python make_bat.py \
    --pair "C:\\Users\\me\\.workbuddy::D:\\FutureWay\\_runtime\\workbuddy" \
    --pair "C:\\Users\\me\\AppData\\Local\\ms-playwright::D:\\FutureWay\\_runtime\\ms-playwright" \
    --exe WorkBuddy.exe --out "D:\\FutureWay\\_runtime"
"""

from __future__ import annotations

import argparse
import datetime
import locale
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BAD_CHARS = '%!^&"'


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def human(n):
    if n is None:
        return "-"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def dir_size(path):
    total = 0
    stack = [path]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_dir():
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def write_text(path, text, crlf=True, encoding="utf-8"):
    nl = "\r\n" if crlf else "\n"
    with open(path, "w", encoding=encoding, newline=nl) as f:
        f.write(text)
    return len(text.encode(encoding, errors="replace"))


def bat_encoding(text):
    """含非 ASCII 时按系统 ANSI 写（cmd 读 .bat 用的是 ANSI 码页，不是 UTF-8）。"""
    try:
        text.encode("ascii")
        return "ascii", False
    except UnicodeEncodeError:
        try:
            enc = locale.getpreferredencoding(False) or "mbcs"
            text.encode(enc)
            return enc, True
        except (LookupError, UnicodeEncodeError):
            return "mbcs", True


# --------------------------------------------------------------------------- #
# 参数解析
# --------------------------------------------------------------------------- #
class Pair:
    def __init__(self, idx, src, dst):
        self.idx = idx
        self.src = src
        self.dst = dst
        self.old = src + "_old"

    @property
    def src_drive(self):
        return self.src[:2].upper()


def parse_pairs(raw_list, do_size=True):
    pairs = []
    seen = set()
    for i, raw in enumerate(raw_list, 1):
        if "::" not in raw:
            raise SystemExit(f"[ERROR] --pair 必须写成 \"源::目标\"，收到: {raw}")
        src, dst = [p.strip().strip('"') for p in raw.split("::", 1)]
        src = os.path.normpath(os.path.abspath(src))
        dst = os.path.normpath(os.path.abspath(dst))
        for p in (src, dst):
            hits = [c for c in BAD_CHARS if c in p]
            if hits:
                raise SystemExit(f"[ERROR] 路径含 cmd 特殊字符 {hits}，请先改名: {p}")
        if not os.path.isdir(src):
            raise SystemExit(f"[ERROR] 源目录不存在: {src}")
        if os.path.normcase(src) == os.path.normcase(dst):
            raise SystemExit(f"[ERROR] 源和目标相同: {src}")
        if os.path.normcase(src) in seen:
            raise SystemExit(f"[ERROR] 源目录重复: {src}")
        seen.add(os.path.normcase(src))
        if dst[:2].upper() == "C:":
            print(f"[WARN] 目标仍在 C 盘，搬了等于没搬: {dst}")
        pair = Pair(i, src, dst)
        pair.size = dir_size(src) if do_size else None
        pairs.append(pair)
    return pairs


# --------------------------------------------------------------------------- #
# bat 生成
# --------------------------------------------------------------------------- #
def set_vars(pairs):
    lines = []
    for p in pairs:
        lines.append(f'set "SRC{p.idx}={p.src}"')
        lines.append(f'set "DST{p.idx}={p.dst}"')
        lines.append(f'set "OLD{p.idx}={p.old}"')
    return "\n".join(lines)


def exe_check(exe, indent=""):
    if not exe:
        return (
            f'{indent}echo   [info] no process check (no --exe given)\n'
            f'{indent}echo          make sure the program using this data is CLOSED.\n'
            f'{indent}echo.'
        )
    return (
        f'{indent}tasklist /FI "IMAGENAME eq {exe}" 2>nul | find /I "{exe}" >nul\n'
        f'{indent}if not errorlevel 1 (\n'
        f'{indent}  echo   [ERROR] {exe} is STILL RUNNING. Quit it completely first.\n'
        f'{indent}  goto :fail\n'
        f'{indent})\n'
        f'{indent}echo   [ok] {exe} is not running'
    )


def gen_copy(pairs, title, logdir):
    body = f"""@echo off
setlocal
title {title} - STEP 1 COPY

set "LOGDIR={logdir}"
{set_vars(pairs)}

cls
echo ============================================================
echo   STEP 1  FULL COPY   (you can keep the program running)
echo ------------------------------------------------------------
echo   This copies every source to its target. Nothing is deleted.
echo   Files that the program is writing right now may fail here;
echo   STEP 2 will re-sync them, so that is expected.
echo ============================================================
echo.
if not exist "%LOGDIR%\\" mkdir "%LOGDIR%"
set "BAD="
"""
    for p in pairs:
        body += f"""
echo [copy {p.idx}/{len(pairs)}] {p.src}
echo          -^> {p.dst}
robocopy "%SRC{p.idx}%" "%DST{p.idx}%" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /MT:16 /NFL /NDL /NP /LOG:"%LOGDIR%\\copy_{p.idx}.log"
set "RC=%ERRORLEVEL%"
echo          robocopy exit=%RC%   (0-7 ok, 8+ error)
if %RC% GEQ 8 set "BAD=1"
"""
    body += """
echo.
echo [diff] listing files still missing on the target side ...
"""
    for p in pairs:
        body += (
            f'robocopy "%SRC{p.idx}%" "%DST{p.idx}%" /E /L /XJ /FP /NDL /NJH /NJS /NP'
            f' /LOG:"%LOGDIR%\\diff_{p.idx}.log"\n'
        )
    body += """
echo        (the diff logs above should only contain files the
echo         program writes while running - those are re-synced
echo         in STEP 2, that is normal)
echo.
if defined BAD (
  echo   [!!] some robocopy runs returned 8 or higher - check the logs in %LOGDIR%
) else (
  echo   [ok] copy finished
)
echo.
echo NEXT: run 2_cutover.bat  (quit the program FIRST)
echo.
pause
exit /b 0
"""
    return body


def gen_cutover(pairs, title, logdir, exe):
    n = len(pairs)
    pre = ""
    for p in pairs:
        pre += f"""if not exist "%SRC{p.idx}%\\" (echo   [ERROR] source not found: %SRC{p.idx}% & goto :fail)
if not exist "%DST{p.idx}%\\" (echo   [ERROR] target not found: %DST{p.idx}% - run 1_copy.bat first & goto :fail)
if exist "%OLD{p.idx}%\\" (echo   [ERROR] %OLD{p.idx}% already exists - resolve it first & goto :fail)
"""

    sync = ""
    for p in pairs:
        sync += f"""echo [2/5] final sync {p.idx}/{n} ...
robocopy "%SRC{p.idx}%" "%DST{p.idx}%" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /MT:16 /NFL /NDL /NP /LOG:"%LOGDIR%\\sync_{p.idx}.log"
if errorlevel 8 (echo   [ERROR] robocopy failed: %SRC{p.idx}% & goto :fail)
echo        ok
"""

    rename = ""
    for p in pairs:
        rename += f"""move "%SRC{p.idx}%" "%OLD{p.idx}%"
if errorlevel 1 (
  echo   [ERROR] cannot rename %SRC{p.idx}%
  echo           something still locks it - close Git Bash / VS Code / Explorer windows
  goto :fail
)
echo        renamed to %OLD{p.idx}%
"""

    link = ""
    for p in pairs:
        link += f"""mklink /J "%SRC{p.idx}%" "%DST{p.idx}%"
if errorlevel 1 (echo   [ERROR] mklink failed: %SRC{p.idx}% & goto :rollback_now)
echo        linked %SRC{p.idx}%
"""

    verify = ""
    for p in pairs:
        verify += f"""fsutil reparsepoint query "%SRC{p.idx}%" >nul 2>&1
if errorlevel 1 (echo   [FAIL] %SRC{p.idx}% is NOT a junction & goto :rollback_now)
if not exist "%DST{p.idx}%\\" (echo   [FAIL] target unreachable: %DST{p.idx}% & goto :rollback_now)
echo        [PASS] {p.src}
"""

    undo = ""
    for p in pairs:
        undo += f"""if exist "%SRC{p.idx}%\\" (
  fsutil reparsepoint query "%SRC{p.idx}%" >nul 2>&1 && rmdir "%SRC{p.idx}%"
)
if exist "%OLD{p.idx}%\\" move "%OLD{p.idx}%" "%SRC{p.idx}%"
"""

    old_list = "".join(f"echo     %OLD{p.idx}%\n" for p in pairs)

    return f"""@echo off
setlocal
title {title} - STEP 2 CUTOVER

set "LOGDIR={logdir}"
{set_vars(pairs)}

cls
echo ============================================================
echo   STEP 2  CUTOVER   (safe and reversible)
echo ------------------------------------------------------------
echo   BEFORE RUNNING:
echo     1. Quit the program completely (tray icon - right click - Quit)
echo     2. Close VS Code (the CodeBuddy extension shares the runtime)
echo     3. Close every Git Bash / terminal window
echo ------------------------------------------------------------
echo   This script ONLY copies, renames and links.
echo   It deletes NOTHING. If any step fails it rolls back.
echo ============================================================
echo.
{exe_check(exe)}
echo.
echo [1/5] preflight ...
if not exist "%LOGDIR%\\" mkdir "%LOGDIR%"
{pre}echo        ok
echo.
{sync}
echo [3/5] renaming originals (reversible) ...
{rename}
echo [4/5] creating directory junctions ...
{link}
echo [5/5] verifying ...
{verify}
echo.
echo ============================================================
echo   DONE. Old data is still on disk at:
{old_list}echo ------------------------------------------------------------
echo   NEXT:
echo     1) Start the program and check everything:
echo        skills / memory / automations / connectors / one real task
echo     2) All good ?      run 3_cleanup.bat  (frees the C: space)
echo     3) Something off ? run 9_rollback.bat (puts it all back)
echo ============================================================
echo.
pause
exit /b 0

:rollback_now
echo.
echo [ROLLBACK] undoing the junction step ...
{undo}echo        rollback finished - original layout restored, nothing deleted
goto :fail

:fail
echo.
echo *** ABORTED - nothing was deleted. Read the messages above. ***
echo.
pause
exit /b 1
"""


def gen_cleanup(pairs, title, exe):
    checks = ""
    for p in pairs:
        checks += f"""fsutil reparsepoint query "%SRC{p.idx}%" >nul 2>&1
if errorlevel 1 (
  echo   [ERROR] %SRC{p.idx}% is NOT a junction.
  echo           Cleanup would be dangerous. Run 9_rollback.bat instead.
  goto :fail
)
"""
    deletes = ""
    for p in pairs:
        deletes += f"""if exist "%OLD{p.idx}%\\" ( rd /s /q "%OLD{p.idx}%" & echo        deleted %OLD{p.idx}% ) else ( echo        [!] %OLD{p.idx}% not found )
"""
    drives = sorted({p.src_drive for p in pairs})
    free = "".join(f"fsutil volume diskfree {d}\n" for d in drives)

    body = f"""@echo off
setlocal
title {title} - STEP 3 CLEANUP

{set_vars(pairs)}

cls
echo ============================================================
echo   STEP 3  CLEANUP
echo ------------------------------------------------------------
echo   ***  W A R N I N G  ***
echo   This PERMANENTLY DELETES the old copies on the system drive.
echo   It does NOT go to the Recycle Bin on purpose - putting them
echo   there would not free any space, which is the whole point.
echo ------------------------------------------------------------
echo   ONLY run this after you verified:
echo     - the program starts normally
echo     - skills / memory / automations are all there
echo   ------------------------------------------------------------
echo   If anything looks wrong, run 9_rollback.bat INSTEAD.
echo ------------------------------------------------------------
echo   Will delete:
"""
    for p in pairs:
        body += f"echo     %OLD{p.idx}%\n"
    body += f"""echo ============================================================
echo.
echo Type YES (all capitals) and press Enter to continue.
echo Just close this window to cancel.
set /p CONFIRM=CONFIRM: 
if /I not "%CONFIRM%"=="YES" (
  echo Cancelled. Nothing was deleted.
  pause
  exit /b 0
)
echo.
{exe_check(exe)}
echo.
echo [1/3] sanity check: every source must still be a junction ...
{checks}echo        ok
echo [2/3] deleting old copies ...
{deletes}
echo [3/3] disk free space now:
{free}echo.
echo Cleanup done.
echo.
pause
exit /b 0

:fail
echo.
echo *** ABORTED - nothing was deleted. ***
echo.
pause
exit /b 1
"""
    return body


def gen_rollback(pairs, title, exe):
    undo = ""
    for p in pairs:
        undo += f"""if exist "%SRC{p.idx}%\\" (
  fsutil reparsepoint query "%SRC{p.idx}%" >nul 2>&1
  if errorlevel 1 (
    echo        [!] %SRC{p.idx}% is a REAL directory, not a junction - left untouched
  ) else (
    rmdir "%SRC{p.idx}%"
    echo        removed junction: %SRC{p.idx}%
  )
)
if exist "%OLD{p.idx}%\\" ( move "%OLD{p.idx}%" "%SRC{p.idx}%" & echo        restored %SRC{p.idx}% ) else ( echo        [!] %OLD{p.idx}% not found - already restored? )
"""
    verify = ""
    for p in pairs:
        verify += f"""fsutil reparsepoint query "%SRC{p.idx}%" >nul 2>&1
if errorlevel 1 (echo        [ok] %SRC{p.idx}% is a real directory again) else (echo        [!!] %SRC{p.idx}% is still a junction)
"""

    return f"""@echo off
setlocal
title {title} - ROLLBACK

{set_vars(pairs)}

cls
echo ============================================================
echo   ROLLBACK
echo ------------------------------------------------------------
echo   Put the original layout back.
echo     - removes the directory junctions (links only)
echo     - renames the _old folders back to their original names
echo     - DATA ON THE TARGET DRIVE IS NOT TOUCHED
echo ------------------------------------------------------------
echo   Quit the program before running this.
echo ============================================================
echo.
{exe_check(exe)}
echo.
echo [1/2] undoing ...
{undo}
echo [2/2] verifying ...
{verify}
echo.
echo Rollback finished. Start the program and confirm it is back to normal.
echo.
pause
exit /b 0

:fail
echo.
echo *** ABORTED ***
echo.
pause
exit /b 1
"""


# --------------------------------------------------------------------------- #
# 说明文档
# --------------------------------------------------------------------------- #
def gen_doc(pairs, outdir, title):
    total = sum(p.size or 0 for p in pairs)
    rows = "\n".join(
        f"| {p.idx} | `{p.src}` | `{p.dst}` | {human(p.size)} |" for p in pairs
    )
    return f"""# {title} · 操作说明

> 生成时间：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
> 目标：把写死在系统盘的数据目录搬到非系统盘，用**目录联接（junction）**让程序路径不变。
> **全程可逆；在你亲自确认一切正常之前，不删除任何东西。**

## 一、搬迁清单

| # | 源（原路径，保持不变） | 目标（真实数据新家） | 体积 |
|---|---|---|---|
{rows}

合计：**{human(total)}**

## 二、原理（30 秒）

```
搬之前：  <源路径>\\            ──▶  真实数据（占系统盘）
搬之后：  <源路径>\\  ══►  <目标路径>\\   ← 真实数据
          ↑ 这里变成一个目录联接，程序毫无感觉
```

`mklink /J` 是目录联接：**不需要管理员权限**，对程序完全透明，随时可拆。

## 三、按顺序执行

### Step 1 · 复制（程序可以照常开着）

双击 **`1_copy.bat`**。
退出码 `0–7` 正常，`8` 以上才是失败。运行中被占用的文件会复制失败 —— **这是正常的**，Step 2 会补齐。

### Step 2 · 切换（必须先彻底退出程序）

先确认三件事：

1. 程序**完全退出**（托盘图标右键 → 退出，关窗口不算）
2. VS Code 已关闭（CodeBuddy 插件共用同一套运行时）
3. 所有 Git Bash / 终端窗口已关闭（PortableGit 就住在数据目录里）

然后双击 **`2_cutover.bat`**。它会依次做五步，每个目录打印 `[PASS]` 才算成功：

| 步骤 | 动作 | 会不会删东西 |
|---|---|---|
| 1/5 | 预检源/目标/旧目录 | 否 |
| 2/5 | 增量同步（补齐 Step 1 漏掉的） | 否 |
| 3/5 | 原目录**改名**为 `<原名>_old` | 否 |
| 4/5 | 在原位建目录联接 | 否 |
| 5/5 | 逐个校验是不是联接、目标是否可达 | 否 |

任何一步失败会自动回滚。

### Step 3 · 验收

启动程序，逐项过：

- [ ] 程序能正常启动
- [ ] 技能 / 插件还在
- [ ] 记忆、历史会话还能翻
- [ ] 自动化任务条数没变
- [ ] 随便干一件真实活能成功
- [ ] 系统盘剩余空间明显变大（资源管理器里原目录显示很小是正常的）

### Step 4 · 清理（建议观察 3–7 天后再做）

双击 **`3_cleanup.bat`**，手输 `YES`。
它会先校验每个源路径**仍是联接**才动手 —— 这一条是为了防止"把真目录删了"。

## 四、出问题怎么办

双击 **`9_rollback.bat`**：删掉联接、把 `_old` 改回原名，**目标盘数据一个字节不动**。
回滚后程序立刻回到搬迁前的状态。

## 五、产物位置

| 文件 | 用途 |
|---|---|
| `1_copy.bat` | 第一遍全量复制 |
| `2_cutover.bat` | 切换（复制增量 → 改名 → 建联接 → 校验） |
| `3_cleanup.bat` | 删旧副本（唯一会删数据的脚本） |
| `9_rollback.bat` | 回滚 |
| `操作说明.md` | 本文件 |

日志默认写在 `{os.path.join(outdir, "_logs")}`。

## 六、四个常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 改名失败 | 还有进程占着目录（Git Bash 最常见） | 关掉所有终端再跑 |
| "您没有足够的权限" | 用了符号链接 `/D` | 本套脚本用 `/J`，不会遇到 |
| 搬完程序像被重置 | 忘了在原路径建联接 | 跑 `9_rollback.bat` 重来 |
| 搬完系统盘没变大 | 旧副本还没删（Step 4 没做） | 验收通过后跑 `3_cleanup.bat` |

## 七、一句话

> 不改路径，改落地。数据搬走、原位留一个"传送门"，程序毫无感觉，出问题一条命令退回去。
"""


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="生成迁移四件套 bat + 中文操作说明")
    ap.add_argument("--pair", action="append", required=True,
                    metavar="SRC::DST", help='源目录::目标目录，可重复多次')
    ap.add_argument("--out", required=True, help="产出目录（必须已存在）")
    ap.add_argument("--exe", default="WorkBuddy.exe", help="需要先退出的进程名，留空表示不检查")
    ap.add_argument("--title", default="WorkBuddy C drive friendly", help="脚本文档标题（建议 ASCII）")
    ap.add_argument("--logdir", default=None, help="日志目录，默认为 <out>/_logs")
    ap.add_argument("--no-size", action="store_true", help="跳过体积统计（更快）")
    ap.add_argument("--no-copy", action="store_true", help="不生成 1_copy.bat")
    args = ap.parse_args(argv)

    outdir = os.path.abspath(args.out)
    if not os.path.isdir(outdir):
        raise SystemExit(f"[ERROR] 产出目录不存在: {outdir}（先建好，或确认盘符拼写）")
    logdir = os.path.abspath(args.logdir) if args.logdir else os.path.join(outdir, "_logs")

    pairs = parse_pairs(args.pair, do_size=not args.no_size)
    files = []

    jobs = []
    if not args.no_copy:
        jobs.append(("1_copy.bat", gen_copy(pairs, args.title, logdir)))
    jobs.append(("2_cutover.bat", gen_cutover(pairs, args.title, logdir, args.exe)))
    jobs.append(("3_cleanup.bat", gen_cleanup(pairs, args.title, args.exe)))
    jobs.append(("9_rollback.bat", gen_rollback(pairs, args.title, args.exe)))

    print(f"[1/2] 生成 bat（{len(pairs)} 组路径）")
    for name, text in jobs:
        path = os.path.join(outdir, name)
        enc, non_ascii = bat_encoding(text)
        size = write_text(path, text, crlf=True, encoding=enc)
        files.append(path)
        note = f"  (含非 ASCII 路径，按 {enc} 编码)" if non_ascii else ""
        print(f"      {name:<16} {size:>7} bytes  CRLF{note}")

    print("[2/2] 生成中文说明")
    doc_path = os.path.join(outdir, "操作说明.md")
    write_text(doc_path, gen_doc(pairs, outdir, args.title), crlf=True, encoding="utf-8")
    files.append(doc_path)
    print(f"      操作说明.md")

    print("\n完成。执行顺序：")
    if not args.no_copy:
        print("  1) 1_copy.bat     程序可开着")
    print("  2) 2_cutover.bat  必须彻底退出程序后")
    print("  3) 验收程序，正常后 3_cleanup.bat")
    print("  4) 有问题就跑 9_rollback.bat")
    print(f"\n产出目录：{outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
