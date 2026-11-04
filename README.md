# 🧰 SYMUN Skills

#### 广西·思源模拟联合国大会的公开技能集

这里的每个 Skill 都是 Agent 能直接加载的结构化指令集，遵循 [Agent Skills 开放标准](https://openagentskills.dev/docs/specification)。Claude Code、Codex、CodeBuddy、Cursor 等支持该标准的工具都能装。

* * *

## 📋 目录

| 名字 | 一句话 | 讲解 |
|---|---|---|
| **write-official-document-like-mxy-jr**（像MXY.jr那样写公文.1.0） | 蒸馏蒙贤熠（MXY.jr）六届「思源」大会的公文写作能力与文风，用来写邀请函、秘书长致辞、活动方案、背景文件 | [详情](#-write-official-document-like-mxy-jr像mxyjr那样写公文10) |

* * *

## 📦 安装方式

在 Claude Code、Codex 等支持 Agent Skills 的工具里，直接说：

```
帮我安装这个 skill：https://github.com/GXSiYuanMUN/SYMUN-skills/tree/main/write-official-document-like-mxy-jr
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
# 把 write-official-document-like-mxy-jr 目录复制到项目的 .claude/skills/ 或全局的 ~/.claude/skills/
```

* * *

## ✨ Skills

### ✍️ write-official-document-like-mxy-jr（像MXY.jr那样写公文.1.0）

> *"愿吾等联合国之子民，为更美好之世界而联合。"*

**它只解决一件事：把"活动方案 / 邀请函 / 致辞"写成蒙贤熠会写的样子。**

不是给你一个公文模板，而是把六届「广西·思源模拟联合国大会」公文里那套稳定的写法拆出来，交给 Agent 用。

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
│   ├── 03-历届主题与时事档案.md  六届主题/议题/时事结合实例逐条拆解
│   └── 04-原文选段.md     致辞×3 + 邀请函×5 + 方案×2 原文选段
└── scripts/
    └── style_check.py    风格自检脚本：14 项指标，输出评分与改进项
```

**内置的风格自检**

写完稿子跑一遍，14 项指标逐项打分，告诉你哪里不像：

```bash
python write-official-document-like-mxy-jr/scripts/style_check.py 稿件.md
```

检测感叹号密度、网络用语、四字格密度、引证密度、平均句长、长句占比、被动句占比、段落长度、三分句式密度、AI 味禁用词、标志性收束、落款署名。

阈值不是拍脑袋定的，是用蒙贤熠的真实原文反标定出来的：

| 样本 | 得分 | 退出码 |
|---|---|---|
| 第二届秘书长致辞原文 | 100 | 0 |
| 第六届活动方案「大会目的及意义」正文 | 94 | 0 |
| 一篇 AI 味的反面样本 | 62.5 | 1 |

→ [脚本完整说明](write-official-document-like-mxy-jr/scripts/style_check.py)

* * *

## 🌟 关于

这里是广西·思源模拟联合国大会的公开技能集。技能来自组委会实际写过、办过的材料——每一届的方案、邀请函、致辞，都是先在真实办会里跑通，才搬出来开源的。

有问题或建议，欢迎在 Issues / Discussions 里说一声。

* * *

MIT License · 自由使用 / 修改 / 再分发
