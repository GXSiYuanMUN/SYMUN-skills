# 🧰 SYMUN Skills

#### 广西·思源模拟联合国大会的公开技能集

这里的每个 Skill 都是 Agent 能直接加载的结构化指令集，遵循 [Agent Skills 开放标准](https://openagentskills.dev/docs/specification)。DeepSeek Haness、WorkBuddy、Claude Code、Codex、CodeBuddy、Cursor 等支持该标准的工具都能装。

* * *

## 📋 目录

| 名字 | 一句话 | 讲解 |
|---|---|---|
| **write-official-document-like-mxy-jr**（像MXY.jr那样写公文.1.0） | 蒸馏蒙贤熠（MXY.jr）亲笔所写公文的写作能力与文风，用来写邀请函、秘书长致辞、活动方案、背景文件 | [详情](#-write-official-document-like-mxy-jr像mxyjr那样写公文10) |
| **workbuddy-c-drive-friendly**（WorkBuddy C 盘友好版.1.0） | 只读体检系统盘占用，用 robocopy + 目录联接（`mklink /J`）把 WorkBuddy 写死在 C 盘的运行态整体搬到非系统盘，原路径不变、失败可一键回滚 | [详情](#-workbuddy-c-drive-friendlyworkbuddy-c-盘友好版10) |

> 本仓库以大会技能为主，也收纳经过实战验证的 **Agent 效率工具**——它们同样来自真实办会与真实办公里的痛点，只是不以公文为主题。

* * *

## 📦 安装方式

在DeepSeek Haness、WorkBuddy、 Claude Code、Codex 等支持 Agent Skills 的工具里，直接说：

```
帮我安装这个 skill：https://github.com/GXSiYuanMUN/SYMUN-skills/tree/main/skills/write-official-document-like-mxy-jr
```

Agent 会自己 clone 到对应目录，不用你操心路径。

安装时保留整个 Skill 目录，包括 `references/`、`scripts/`、`assets/`（如有）。只粘贴 `SKILL.md` 可以参考方法，但不能替代配套脚本和资源。普通聊天模型没有文件或联网工具时，无法完成实时检索或生成文件；请用具备相应工具的 Agent。搜索工具不限模型或厂商。

Claude Code 也可通过插件目录安装全部 Skill：

```
/plugin marketplace add GXSiYuanMUN/SYMUN-skills
/plugin install symun-skills@symun-skills
```

更新时使用 `/plugin marketplace update symun-skills`，再 `/plugin update symun-skills@symun-skills`；是否自动更新取决于客户端设置。避免同时保留同名插件安装和手动复制版本。

也可以用 skills CLI 一键安装：

```
npx skills add GXSiYuanMUN/SYMUN-skills --skill write-official-document-like-mxy-jr
```

手动安装（以 Claude Code 为例）：

```bash
git clone https://github.com/GXSiYuanMUN/SYMUN-skills.git
# 把 skills/write-official-document-like-mxy-jr 目录复制到项目的 .claude/skills/ 或全局的 ~/.claude/skills/
```

* * *

## 🗂 仓库结构

```
SYMUN-skills/
├── skills/                          每个 Skill 一个独立目录
│   ├── write-official-document-like-mxy-jr/
│   │   ├── SKILL.md                 必需：frontmatter + 指令正文
│   │   ├── references/              按需加载的参考文档
│   │   ├── scripts/                 可执行脚本
│   │   └── LICENSE.txt
│   └── workbuddy-c-drive-friendly/
│       ├── SKILL.md
│       ├── references/              决策依据、布局、坑、实战记录
│       ├── scripts/                 diagnose / make_bat / list_automations
│       └── LICENSE.txt
├── scripts/validate_skills.py       仓库级：规范校验（CI 自动调用）
├── .claude-plugin/marketplace.json  插件市场清单
├── .github/                         CI、Issue 与 PR 模板
├── CONTRIBUTING.md                  贡献指南（含素材归属要求）
├── CHANGELOG.md                    更新日志
└── LICENSE                          MIT
```

**新增 Skill**：放在 `skills/` 下，目录名必须与 `SKILL.md` 的 `name` 完全一致。
提交前跑一遍 `python scripts/validate_skills.py`。

* * *

## ✨ Skills

### ✍️ write-official-document-like-mxy-jr（像MXY.jr那样写公文.1.0）

> *"愿吾等联合国之子民，为更美好之世界而联合。"*

**它只解决一件事：把"活动方案 / 邀请函 / 致辞"写成蒙贤熠会写的样子。**

不是给你一个公文模板，而是把「广西·思源模拟联合国大会」那些稿子里那套稳定的写法拆出来，交给 Agent 用。

**关于素材范围**：本技能收录的样本，全部出自本技能作者本人手笔——**第二、三、四、六届**的邀请函与秘书长致辞，以及**第三至六届**的活动方案。第五届的邀请函与致辞由该届秘书长撰写，**不属本技能作者作品，已排除**（第五届的活动方案仍由本技能作者主笔，其主题凝练与议题阐释是有效样本）。

**为什么要拆文风，不给模板**

一个"模联活动方案模板"人人能写。但真正让这些稿子有辨识度的不是格式，是三样东西：

1. **主题、时代、青年三层咬合**——主题挂在当年真实发生的重大节点上（联大主题、周年纪念、中央文件），中间是三到四个不同领域的具体困难，最后落到一个身份具体的年轻人和一件具体的事上。三层不咬住，稿子立刻塌成万能模板。
2. **议题阐释的三段式**——历史演进与治理形势 / 本议题旨在…… / 议题设置的考量与价值。第三段用「区别于……区别在于……视角的 X 使得……」这个句式，把"为什么用这个会场机制讨论这个议题"讲透。
3. **零感叹号**——蒙贤熠的稿子通篇没有一个感叹号。情绪全部由动词、意象和排比承载。这是第一道红线，也是最容易被 AI 破坏的一条。

**怎么触发**

```
帮我写第七届思源模拟联合国大会的邀请函，主题是"XXX"
帮我凝练一下下一届大会的主题，给几个候选
帮我写一份活动方案的第二部分"大会选题介绍、阐释及展望"
帮我把这份致辞改成蒙贤熠的文风
检查这份稿子像不像 MXY 写的
```

**用之前必须先给主题。** 主题没定，Agent 会拒绝动笔——因为主题决定了后面所有的时事选择、议题安排和价值落点。

**它长什么样**

```
symun-gov-doc-writer/
├── SKILL.md              主文件：工作流、体裁路由表、六条铁律
├── references/
│   ├── 01-写作能力.md     主题三问、议题契合逻辑、时事检索与结合、九部分骨架
│   ├── 02-文风基因.md     语气定位、句法节奏、意象系统、四级引证表、禁忌清单
│   ├── 03-历届主题与时事档案.md  六届主题/议题/时事结合实例拆解（标注作者归属）
│   └── 04-原文选段.md     致辞×3 + 邀请函×5 + 方案×2 原文选段
└── scripts/
    └── style_check.py    风格自检脚本：14 项指标，输出评分与改进项
```

**内置的风格自检**

写完稿子跑一遍，14 项指标逐项打分，告诉你哪里不像：

```bash
python skills/write-official-document-like-mxy-jr/scripts/style_check.py 稿件.md
```

检测感叹号密度、网络用语、四字格密度、引证密度、平均句长、长句占比、被动句占比、段落长度、三分句式密度、AI 味禁用词、标志性收束、落款署名。

阈值不是拍脑袋定的，是用蒙贤熠的真实原文反标定出来的：

| 样本 | 得分 | 退出码 |
|---|---|---|
| 第二届秘书长致辞原文 | 100 | 0 |
| 第六届活动方案「大会目的及意义」正文 | 94 | 0 |
| 一篇 AI 味的反面样本 | 62.5 | 1 |

→ [脚本完整说明](skills/write-official-document-like-mxy-jr/scripts/style_check.py)

* * *

### 🛠️ workbuddy-c-drive-friendly（WorkBuddy C 盘友好版.1.0）

> *"不改路径，改落地。"*

**它解决一件很具体的事：WorkBuddy / CodeBuddy 用久了把 C 盘吃光，而程序里没有任何设置项能改数据目录。**

WorkBuddy 把所有数据写死在 `C:\Users\<你>\.workbuddy`——技能、记忆、自动化库、Python/Node 运行时、浏览器 profile，长期使用会涨到几个 GB；再叠加 `%LOCALAPPDATA%\ms-playwright`（浏览器内核，约 1.4 GB），系统盘就危险了。

这个技能的做法是**数据搬走、原位留一个「传送门」**：

```
搬之前：  C:\Users\<你>\.workbuddy\        真实数据（占用 C 盘）
搬之后：  C:\Users\<你>\.workbuddy\  ══►  E:\FutureWay\_runtime\workbuddy\   ← 真实数据
          （一个目录联接，本身几乎不占空间）
```

程序照旧读写 C 盘那个路径，操作系统自动穿透到新盘。**路径不变 → 配置不用改、历史索引不失联、出问题一条命令退回去。**

**三步走，全程可逆**

1. **体检**（只读，秒级）：`python scripts/diagnose.py` —— 各盘剩余、运行态是否已是联接、哪些目录值得搬、有几个工作区误落在 C 盘
2. **生成切换脚本**：`python scripts/make_bat.py --pair "源::目标" ...` —— 按实际路径生成四件套，不手写 bat
3. **由人亲手执行切换**：完全退出程序后双击 `2_cutover.bat`，每个目录都 `PASS` 即成功；`3_cleanup.bat` 最后才跑，要求手输 `YES`

| 脚本 | 作用 | 会不会删东西 |
|---|---|---|
| `1_copy.bat` | 第一遍全量复制 + 差异清单 | 否 |
| `2_cutover.bat` | 增量同步 → 原目录改名 → 建联接 → 逐项校验，失败自动回滚 | 否 |
| `3_cleanup.bat` | 删除旧副本，前置校验联接在位 | **是**（唯一会删的） |
| `9_rollback.bat` | 删联接 → 原名改回，新盘数据不动 | 否 |

**为什么切换不交给 Agent 自动执行**

Agent 往往就跑在这份数据里。程序运行时改自己的数据目录，会产生「旧句柄指旧路径、新进程指新路径」的混合状态。所以这一步交给人，脚本负责把风险挡在前面。

**三条硬约束（踩过才知道）**

- 目标盘必须是**固定盘**，不能是 U 盘 / 移动硬盘 / 网络盘——掉盘即废
- 判断联接用 `os.readlink()`，**不要用 `os.path.islink()`**——后者对 Windows 目录联接返回 `False`，会让人误判「联接丢了」然后白折腾一轮重建
- **搬迁是止血，不是治本**：实测搬走 6.2 GB 后，C 盘只从 1.2 GB 回升到 2.0 GB，差额被系统更新和其他软件吃掉。它精准解决「某个应用长期膨胀」，不能替代全网盘盘点

**顺手解决的另一个困惑**

升级后「界面里的自动化任务不见了」——九成不是丢了。任务定义在 `workbuddy.db` 的 `automations` 表，靠 `cwds[0]` 绑定到某个工作目录；**你打开的工作区不在它的 `cwds` 里，界面上就是空的**。`scripts/list_automations.py` 会按工作区分组列出全部任务，并体检运行档案是否在位。

**实测过的**

- 19,138 个目录 / 84,711 个文件 / 4.645 GB，首遍复制 **1 分 24 秒**
- 迁移后经历一次版本升级，联接未被破坏，新版自有 SQLite 迁移照常落在新盘
- 四件套在沙箱里跑完整个生命周期：复制 → 切换 → 回滚 → 清理，含「源不是联接时清理脚本必须拒绝执行」这条安全阀

→ [SKILL.md](skills/workbuddy-c-drive-friendly/SKILL.md) · [实战记录与三个月后复核](skills/workbuddy-c-drive-friendly/references/case-study.md) · [12 个真实坑](skills/workbuddy-c-drive-friendly/references/pitfalls.md)

* * *

## 🌟 关于

这里是广西·思源模拟联合国大会的公开技能集。技能来自组委会实际写过、办过的材料——每一届的方案、邀请函、致辞，都是先在真实办会里跑通，才搬出来开源的。

有问题或建议，欢迎在 Issues / Discussions 里说一声。

* * *

MIT License · 自由使用 / 修改 / 再分发
