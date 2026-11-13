# WorkBuddy / CodeBuddy 数据布局与寻址

## 一、四层布局

WorkBuddy（含 CodeBuddy 插件）的数据分四层。**混淆这四层，是"东西是不是丢了""搬完怎么没效果"的头号原因。**

| 层 | 默认位置 | 内容 | 随工作区变 |
|---|---|---|---|
| **资产层** | 用户自定的工作空间根 | 项目代码、文档、`.workbuddy/memory/` 日志 | 每个工作区一套 |
| **运行态层** | `C:\Users\<你>\.workbuddy` | 技能、全局记忆、设置、运行时、浏览器 profile、`workbuddy.db` | 全局唯一 |
| **自动化定义** | 运行态层 `workbuddy.db` → `automations` 表 | prompt、计划、`cwds[0]` 绑定 | 全局唯一 |
| **自动化档案** | 各工作区 `.workbuddy/automations/<id>/` | `memory.md`、消息留档 | 跟工作区走 |

关键推论：

> 自动化的**定义**在全局，**档案**分散在各工作区，两者靠 `cwds[0]` 串起来。
> 当前打开的工作区不在某条任务的 `cwds` 里，界面上就看不到它 —— **任务没丢，只是绑在别处。**

## 二、运行态目录里有什么

```
~/.workbuddy/
├─ workbuddy.db          ← 自动化定义、sessions、workspaces 都在这里
├─ workbuddy.db-wal      ← SQLite WAL，正常存在，不是损坏
├─ MEMORY.md             ← 用户级长期记忆（新版可能已迁到 user-<id>-personal/）
├─ settings.json         ← 全局设置
├─ skills/               ← 技能源，每个技能一个子目录，内含 SKILL.md
├─ binaries/             ← 托管 Python / Node 运行时（体积大头，自动化 prompt 常硬编码引用）
├─ vendor/PortableGit    ← Git Bash 运行时（迁移时必须先关掉所有终端）
├─ projects/ sessions/   ← 会话与项目索引
├─ traces/               ← 调试追踪，可清（旧文件无价值）
├─ plugins/              ← 连接器与插件
└─ <浏览器 profile>/       ← 调试用 profile，含登录态
```

少量配套目录（体积小，通常不动）：

| 路径 | 作用 |
|---|---|
| `%APPDATA%\WorkBuddy` | 应用级数据（窗口状态等） |
| `%LOCALAPPDATA%\CodeBuddyExtension` | VS Code 扩展数据 |
| `~\.codebuddy` | CodeBuddy CLI / 插件数据 |
| `~\.workbuddy-key-fallback` | 密钥回退目录（新版新增） |
| `%LOCALAPPDATA%\ms-playwright` | 浏览器自动化内核 |

## 三、`workbuddy.db` 里的关键表

### `automations`

| 字段 | 含义 |
|---|---|
| `id` | 两种形态：旧 `automation-<13位毫秒时间戳>`、新 `<uuid>` |
| `cwds` | JSON 数组，**`cwds[0]` = 这条自动化绑定的工作目录** |
| `workspace_scope` | `workspace` = 绑在用户工作区；`task` = 其 cwd 其实是任务自建目录（按路径形状回填，**不代表业务类型**） |
| `owner_status` | `legacy_unassigned` = 老版本遗留、尚未认领；`confirmed` = 新版正式建立 |
| `status` | `ACTIVE` / `PAUSED` |
| `deleted_at` | 非空 = 软删除，界面不显示，但仍在表里 |

统计条数时要过滤 `deleted_at is null`，否则会以为"多出来几条"。

### `workspaces`

```sql
CREATE TABLE workspaces (path TEXT PRIMARY KEY, last_opened_at INTEGER NOT NULL);
```

只记路径和最后打开时间。**这就是"把工作区搬到别的盘之后历史记录会对不上"的根源** —— 老路径还留在这张表里。

处置方式有两条：
- **建联接把老路径留住**（推荐）：新路径能用，老路径也还能打开，索引不用改。
- 接受失联：直接换路径，旧条目失效，需重新打开一次建立新条目。

## 四、界面里看不到自动化？按这张表排查

| 症状 | 真实原因 | 处置 |
|---|---|---|
| 界面里看不到自动化 | 当前工作区 ≠ 该自动化的 `cwds[0]` | 打开对应工作区，或用 `scripts/list_automations.py` 确认绑定 |
| 升级后"任务全没了" | 同上；或 `owner_status` 仍是 `legacy_unassigned`，新版要求认领 | 用脚本核对；确认未被软删除 |
| 自动化不执行 | 绑定的工作目录已不存在 / 脚本路径失效 | 脚本会标 `<工作目录已不存在！>`；修目录或改绑定 |
| 档案目录缺失但任务在跑 | 该任务从未在绑定工作区里落过档 | 无害，但会丢历史上下文；在该工作区跑一次即可补上 |
| C 盘又满了 | 运行态确实已搬走，但**另有新目录**落在 C 盘（新版组件、`AppData` 下新东西） | 重新跑 `diagnose.py` 盘点 |
| 两条任务同时触发 | 同 cwd、同计划的重复定义（旧 id 与 uuid 并存） | 只保留一条，另一条软删除 |

## 五、"修路"之后怎么认路

搬迁后 `C:\Users\<你>\.workbuddy` 不再是真目录，而是**目录联接**，指向新位置。

**影响：**

- 所有写死 `C:\Users\<你>\.workbuddy\...` 的脚本、自动化 prompt、技能配置**照常可用**，一个字都不用改
- 程序升级时照常读写这个路径 → **升级不会破坏联接**（实测多次版本升级后联接仍在）
- 但**排查时容易误判**：资源管理器里 C 盘那个目录体积显示很小甚至 0，实际数据在新盘

**判断是不是联接的正确写法：**

```python
import os
p = os.path.expanduser("~/.workbuddy")
try:
    target = os.readlink(p)          # 成功 = 是重解析点
    print("junction ->", target)
except OSError:
    print("real directory")
```

> ⚠️ **不要用 `os.path.islink()` 判断 junction** —— 它对目录联接返回 `False`，会让你误判"联接丢了"然后白折腾一轮。这是本项目修过的一个真实错误。

## 六、搬迁后 / 升级后的体检清单

1. `os.readlink(~/.workbuddy)` 成功，且指向非系统盘
2. 技能数量与升级前一致（`diagnose.py` 会打印）
3. 用户级 `MEMORY.md` 内容还在
4. `automations` 未删除条数与升级前一致
5. C 盘剩余空间没有因升级而大幅回落
6. 程序自有的 SQLite 迁移照常落在新盘（新盘里会出现 `.workbuddy-sqlite-migrations/`）

前 5 项用 `python scripts/diagnose.py --compare baseline.json` 一次就能比完。

## 七、脚本

```bash
python scripts/list_automations.py                 # 按工作区分组列出全部自动化
python scripts/list_automations.py --json          # 机器可读
python scripts/list_automations.py --cwd "E:\proj" # 只看某个工作区
python scripts/list_automations.py --db <path>     # 指定数据库
```

输出包含：数据库真实路径（含联接穿透）、每条任务的工作区 / 状态 / 计划 / **档案是否存在**，结尾给出「档案缺失 N 条、工作目录不存在 M 个」的体检结论。

脚本只读打开数据库；若因 WAL 锁失败，会自动复制快照再读。
