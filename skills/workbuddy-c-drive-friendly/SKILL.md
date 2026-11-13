---
name: workbuddy-c-drive-friendly
display_name: WorkBuddy C 盘友好版.1.0
description: 让 WorkBuddy / CodeBuddy 长期使用不再把 C 盘撑爆。只读体检系统盘占用与运行态真实位置，再用 robocopy 加目录联接（mklink /J）把写死在 C 盘的 ~/.workbuddy、ms-playwright 等数据目录整体搬到非系统盘，原路径保持不变、失败可一键回滚；同时覆盖「工作空间根落在 C 盘」的迁移与目录命名规则，以及搬迁后与版本升级后的联接复查、界面里看不到自动化任务的寻址排查。当用户说 C 盘满了 / C 盘瘦身 / C 盘清理、WorkBuddy 占空间、把 workbuddy 搬到 D 盘或 E 盘、目录联接 / junction / 软链接搬家、迁移工作空间、升级后任务不见了、自动化找不到时使用。
version: 1.0.0
license: MIT
compatibility: 仅 Windows（依赖 NTFS 目录联接与 robocopy）；脚本需 Python 3.9+
metadata:
  author: GXSiYuanMUN
  display_name_zh: WorkBuddy C 盘友好版.1.0
  version: "1.0.0"
  category: tooling
allowed-tools: null
agent_created: true
---

# WorkBuddy C 盘友好版

## 这个技能解决什么

WorkBuddy（含 CodeBuddy 插件）把所有数据写死在 `C:\Users\<你>\.workbuddy`，且**没有设置项能改**。
长期使用后这个目录会涨到几个 GB，叠加 `AppData\Local\ms-playwright`（浏览器内核），系统盘被慢慢吃掉。
更麻烦的是：**界面里看不到自动化任务**，多半不是丢了，而是它绑在另一个工作区上。

本技能做三件事，全部可逆、零删除直到用户亲自确认：

| 能力 | 入口 |
|---|---|
| ① 只读体检：C 盘还差多少、运行态真实在哪、多少 GB 是可搬的 | `scripts/diagnose.py` |
| ② 把运行态搬出 C 盘，原路径用目录联接指回去 | `scripts/make_bat.py` 生成四件套 → 用户执行 |
| ③ 搬迁后 / 升级后复查，以及自动化任务的寻址 | `scripts/diagnose.py --compare`、`scripts/list_automations.py` |

## 何时用 / 何时别用

**用**：
- 系统盘剩余 `< 5 GB` 或 `< 15%`，且大头是 WorkBuddy / 浏览器内核
- 用户说"把 workbuddy 搬到 D 盘 / E 盘，但别让程序坏"
- 用户的工作空间根目录直接建在 `C:\` 下
- 升级 WorkBuddy 后怀疑"搬迁白做了"或"任务没了"

**别用**：
- `Program Files` 下的注册表安装型软件 → 卸载重装到新盘更干净
- 纯缓存（`%TEMP%`、更新缓存、休眠文件）→ 直接清更快，见 `references/decision.md`
- macOS / Linux → 本技能只讲 Windows（NTFS + junction）

## 心智模型：四层布局（先分清，再动手）

混淆这四层，是"东西是不是丢了""搬了怎么没效果"的头号原因。

| 层 | 默认位置 | 内容 | 随工作区变 |
|---|---|---|---|
| **资产层** | 用户自定的工作空间根 | 项目代码、文档、`.workbuddy/memory/` 日志 | 每个工作区一套 |
| **运行态层** | `C:\Users\<你>\.workbuddy` | 技能、全局记忆、设置、Python/Node 运行时、浏览器 profile、`workbuddy.db` | 全局唯一 |
| **自动化定义** | 运行态层的 `workbuddy.db` → `automations` 表 | 每条任务的 prompt、计划、`cwds[0]` 绑定 | 全局唯一 |
| **自动化档案** | 各工作区 `.workbuddy/automations/<id>/` | `memory.md` 等运行留档 | 跟工作区走 |

关键推论：
> **自动化的"定义"在全局，但"档案"分散在工作区，两者靠 `cwds[0]` 串起来。**
> 当前打开的工作区不在某条任务的 `cwds` 里，界面上就看不到它 —— 任务没丢，只是绑在别处。

## 铁律（违反即失败）

1. **只复制、改名、建链接；一个字节都不删**，直到用户亲自确认一切正常。
2. **两遍法**：第一遍在程序运行中全量复制；第二遍在程序**完全退出后**增量同步。
3. **切换动作由用户亲手执行**。Agent 自己往往就跑在这份数据里，程序运行时改自己的目录会产生"句柄指旧路径、新进程指新路径"的混合状态。
4. `.bat` 一律 **ASCII + CRLF**；中文说明单独放 `.md`（cmd 对 UTF-8 无 BOM 脚本解析不可靠）。
5. 删旧副本用 `rd /s /q`（**进回收站不释放空间**，与目的冲突），且必须二次确认 + 前置校验联接在位。
6. 目标盘必须是**固定盘（FIXED）**，不能是 U 盘 / 移动硬盘 / 网络盘 —— 掉盘即废。
7. 用 `mklink /J`（目录联接，无需管理员），**不要**用 `/D`（符号链接，常要管理员权限）。

## 流程 A：把运行态搬出 C 盘

### Step 0 · 体检（只读，先看数字再决定）

```bash
python <skill>/scripts/diagnose.py
```

输出：各盘剩余与百分比、运行态是否已是联接、各候选目录体积、运行态内部 Top 10 大目录、技能与自动化条数、**落在 C 盘的工作区**，最后给一句结论。

判断阈值：系统盘剩余 `< 5 GB` 或 `< 15%` → 立刻处理；单个可搬目录 `> 3 GB` → 值得搬。
**先清一轮可再生成的东西**（`%TEMP%`、`Windows.old`、休眠文件、浏览器缓存），再决定搬多少 —— 见 `references/decision.md`。

### Step 1 · 选盘 + 建根 + 守命名规则

目标盘判据：剩余空间 `> 待搬体积 × 3`，且是固定盘。
根目录名守这几条（**别用空格和中文**，`robocopy` / `mklink` / `cmd` 的引号与编码坑都从这里来）：

| 规则 | 说明 | 好例子 | 坏例子 |
|---|---|---|---|
| 仅 ASCII 字母数字与 `-` | 无空格、无中文 | `D:\FutureWay` | `D:\future way`、`D:\我的空间` |
| 2–20 字符且自解释 | 别缩写到看不懂 | `E:\AIHome` | `E:\x` |
| 非系统盘根下一级 | 不塞进别的软件目录 | `D:\FutureWay` | `C:\FutureWay`、`D:\Program Files\x` |
| 总路径 ≤ 150 字符 | 给 `node_modules` / venv 留余量（Windows 硬限 260） | — | 嵌套 8 层的中文长路径 |

子目录统一模板（`_` 前缀专用于机器数据，`NN_` 前缀专用于资产，永不混放）：

```
<Root>\
├─ _runtime\        ← 机器数据：会膨胀、可重建，单独一处
│  ├─ workbuddy\    ← 目录联接目标
│  ├─ ms-playwright\
│  └─ _logs\
├─ 00_宪法\          ← 协作准则、SOUL/IDENTITY/USER
├─ 01_技能\
├─ 02_记忆\
├─ 03_资产\
├─ 04_项目\
├─ 05_自动化\
└─ 99_归档\
```

`_runtime` 放在根下一级、与资产平级，是刻意的：**资产是你的作品，运行态是机器的排泄物，别让它们抢同一个盘的最后 5 GB。**

### Step 2 · 第一遍全量复制（程序可照常运行）

```bash
robocopy "C:\Users\<你>\.workbuddy" "<Root>\_runtime\workbuddy" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /MT:16 /NFL /NDL /NP /LOG:"<Root>\_runtime\_logs\pass1.log"
```

- `/XJ` 跳过已有联接（防循环）；`/COPY:DAT` 而非 `/COPYALL`（后者要备份权限）
- 退出码 `0–7` 正常，`≥8` 才是失败
- 运行中被占用的 live 文件（`workbuddy.db`、`-wal`、日志）会失败 → **正常**，第二遍补

也可以让脚本生成 `1_copy.bat` 一次跑完所有目录（见 Step 3）。

### Step 3 · 生成切换四件套（不手写 bat）

```bash
python <skill>/scripts/make_bat.py \
  --pair "C:\Users\<你>\.workbuddy::<Root>\_runtime\workbuddy" \
  --pair "C:\Users\<你>\AppData\Local\ms-playwright::<Root>\_runtime\ms-playwright" \
  --exe WorkBuddy.exe --out "<Root>\_runtime"
```

产出（全部 ASCII + CRLF，路径已按你的实际参数填好）：

| 文件 | 作用 | 会不会删东西 |
|---|---|---|
| `1_copy.bat` | 第一遍全量复制 + 差异清单 | 否 |
| `2_cutover.bat` | 增量同步 → 原目录改名 → 建联接 → 逐个校验；失败自动回滚 | **否**（只复制/改名/建链接） |
| `3_cleanup.bat` | 删除 C 盘旧副本；要求手输 `YES` 且先校验联接在位 | 是（唯一会删的） |
| `9_rollback.bat` | 删联接 → 原名改回；目标盘数据不动 | 否（只删链接） |
| `操作说明.md` | 给你的中文步骤说明 | — |

### Step 4 · 用户执行切换

前置三条，缺一即失败：
1. **完全退出** WorkBuddy（托盘图标右键 → 退出，关窗口不算）
2. 关掉 VS Code（CodeBuddy 插件用同一套运行时）
3. 关掉所有 Git Bash / 终端窗口（PortableGit 就住在 `.workbuddy\vendor` 里，开着就改不了名）

然后双击 `2_cutover.bat`。**看到每个目录都 PASS 才是成功。**

### Step 5 · 验收（别靠肉眼）

```bash
python <skill>/scripts/diagnose.py --compare <Root>\_runtime\_baseline.json
```

迁移前先 `--save` 一份基线，迁移后 `--compare` 自动对比：联接是否在位、真实路径、技能数、自动化条数、各盘剩余。逐项一致才算过。

再手动过一遍：启动程序 → 技能在不在 → 记忆在不在 → 自动化条数对不对 → 随便干一件真实活。

### Step 6 · 清理（最后一步，且要等）

一切正常后再跑 `3_cleanup.bat`（需手输 `YES`）。**建议观察 3–7 天**再删 —— 删了就只剩"重搬一遍"这条路。

### Step 7 · 反哺：把布局写进程序能读到的地方

搬迁造成"路径不变、物理位置变了"，这会长期影响后续所有排查。把它写进一条常驻记忆或技能：

```
运行态 ~/.workbuddy 已是目录联接 → <Root>\_runtime\workbuddy
写法仍用 C 盘路径，照常可用；资源管理器里 C 盘那目录体积显示很小是正常的，不是数据丢了
自动化定义在 workbuddy.db 的 automations 表，靠 cwds[0] 绑定工作区；界面看不到不等于丢了
```

## 流程 B：工作空间根落在 C 盘怎么办

`diagnose.py` 会列出所有登记过的工作区，标出**在 C 盘的**那些。处置顺序：

1. **先定新家**：按 Step 1 的命名规则在非系统盘建 `<Root>\04_项目\<项目名>`（或 `<Root>\90_工作区\<原名>`，日期命名的工作区建议原样保留名字，只换盘符）
2. **复制而不是剪切**：`robocopy "<旧>" "<新>" /E /COPY:DAT /DCOPY:DAT /XJ /MT:16`
3. **建联接把老路径留住**：用 `make_bat.py --pair "<旧工作区>::<新工作区>" --exe ""` 生成四件套，跑 `2_cutover.bat`
   —— 为什么不在程序里"换个目录打开"就完事：**旧路径已被 `sessions` / `workspaces` 表和历史会话索引记录在案**，直接换路径会让历史记录失联；建联接则两边都能打开，历史照常可读。
4. **新项目从此刻起直接建在新盘**，别再落回 C 盘

> 一次搬完所有 C 盘工作区前，先算体积并确认目标盘剩余 `> 体积 × 3`。
> 工作区里常有 `node_modules`、`.venv`，这些可以排除掉重建：加 `/XD node_modules .venv __pycache__`。

## 流程 C：升级后 / C 盘又满了

升级（如 5.4 → 5.7）是最容易让人怀疑"联接白做了"的时刻，实际是**联接最稳的时刻**：新版照常读写原路径，自动穿透到新盘。

```bash
python <skill>/scripts/diagnose.py
```

三件事对着看：
1. `运行态` 那行仍显示 `junction -> <非系统盘路径>` → 路还在
2. 技能数、自动化条数、用户级 `MEMORY.md` 与升级前一致
3. C 盘剩余**没有因升级大幅回落**；若回落，多半是升级往 C 盘塞了**新目录**（例如 `AppData` 下新组件），回到 Step 0 重新盘点

**搬迁是止血，不是治本。** 实测过：搬走 6.2 GB 后，C 盘只从 1.2 GB 回升到 2.0 GB —— 差额被系统更新和其他软件吃掉了。要真正宽裕，得单独做一轮全网盘盘点（`references/decision.md` 有清单）。

## 脚本速查

```bash
python <skill>/scripts/diagnose.py                    # 完整体检
python <skill>/scripts/diagnose.py --json              # 机器可读
python <skill>/scripts/diagnose.py --no-size           # 跳过体积统计（秒出）
python <skill>/scripts/diagnose.py --save b.json       # 存基线
python <skill>/scripts/diagnose.py --compare b.json    # 迁移后/升级后对比
python <skill>/scripts/make_bat.py --pair "SRC::DST" ... --exe WorkBuddy.exe --out DIR
python <skill>/scripts/list_automations.py             # 自动化按工作区分组 + 档案体检
```

脚本一律只读，不写任何被检查的目录；`make_bat.py` 只写 `--out` 指定目录。

## 参考文件

| 文件 | 什么时候读 |
|---|---|
| `references/decision.md` | 判断该不该搬、选哪个盘、先清什么、命名与目录树的完整规则 |
| `references/layout.md` | 三层布局细节、`automations` / `workspaces` 表字段、界面看不到任务的原因表 |
| `references/pitfalls.md` | 12 个真实坑与症状对照（含"搬完 C 盘又满了""升级后误判"） |
| `references/case-study.md` | 一次完整实战的脱敏数据：体积、耗时、耗时点、复核结论 |

## 一句话总结

> **不改路径，改落地。** 数据搬走、原位留一个"传送门"（目录联接），程序毫无感觉，出问题一条命令退回去。

> 本技能由 `win-c-drive-relocate`（怎么搬）与 `workbuddy-runtime-layout`（搬完怎么认路）两套实践合并而成，并修正了旧版验收命令的一个错误判据（`os.path.islink()` 对 junction 返回 `False`，不能用于判断联接是否存在）。
