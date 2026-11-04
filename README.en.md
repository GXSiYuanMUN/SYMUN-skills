# SYMUN Skills

#### Public skill collection from Guangxi Siyuan Model United Nations Conference

Every Skill here is a structured instruction set that agents can load directly, following the [Agent Skills open standard](https://openagentskills.dev/docs/specification). It works in Claude Code, Codex, CodeBuddy, Cursor, and any other tool that supports the standard.

* * *

## 📋 Contents

| Name | One-liner | Docs |
|---|---|---|
| **write-official-document-like-mxy-jr** (Chinese display name: 像MXY.jr那样写公文.1.0) | Distills Meng Xianyi's (MXY.jr) official-document writing ability and style across six consecutive Siyuan MUN conferences — for invitations, secretary-general addresses, event proposals, and background papers | [Details](#-write-official-document-like-mxy-jr) |

* * *

## 📦 Installation

In any Agent Skills-compatible tool (Claude Code, Codex, etc.), just say:

```
帮我安装这个 skill：https://github.com/GXSiYuanMUN/SYMUN-skills/tree/main/write-official-document-like-mxy-jr
```

The agent clones the directory itself — you don't need to worry about paths.

Keep the whole skill directory when installing, including `references/`, `scripts/`, and `assets/` (if present). Copying only `SKILL.md` is enough to reference the method, but it does not replace the bundled scripts and resources. A plain chat model without file or network access cannot perform live research or generate files — use an agent with the corresponding tools. Search tools are not restricted by model or vendor.

Claude Code can also install all skills via the plugin marketplace:

```
/plugin marketplace add GXSiYuanMUN/SYMUN-skills
/plugin install symun-skills@symun-skills
```

To update: `/plugin marketplace update symun-skills`, then `/plugin update symun-skills@symun-skills`. Whether updates apply automatically depends on client settings. Avoid keeping both a plugin install and a manually copied version under the same name.

One-command install with the skills CLI:

```
npx skills add GXSiYuanMUN/SYMUN-skills --skill write-official-document-like-mxy-jr
```

Manual install (Claude Code example):

```bash
git clone https://github.com/GXSiYuanMUN/SYMUN-skills.git
# copy the write-official-document-like-mxy-jr directory into .claude/skills/ or ~/.claude/skills/
```

* * *

## ✨ Skills

### ✍️ write-official-document-like-mxy-jr

> *"愿吾等联合国之子民，为更美好之世界而联合。"*

**It solves exactly one thing: making event proposals, invitations, and addresses read the way Meng Xianyi writes them.**

This is not a template. It decomposes the stable techniques behind six consecutive Siyuan MUN conference document sets into something an agent can apply.

**Why decompose style instead of shipping a template**

Anyone can write a "MUN event proposal template." What actually gives these documents their identity is three things:

1. **The three-layer interlock — theme, era, youth.** The theme hangs on a real, dated event (a UN General Assembly theme, an anniversary, a central-party document); the middle layer names three or four concrete difficulties across *different* fields; the last layer lands on a specific young person and a specific thing to do. When the three layers fail to interlock, the document collapses into a universal template.
2. **The three-part committee rationale.** Historical evolution and the governance situation / what this committee aims to achieve / the considerations behind the committee design. The third part uses the pattern *"区别于……区别在于……视角的 X 使得……"* to explain *why this committee mechanism* fits *this issue*.
3. **Zero exclamation marks.** Not one `!` appears across Meng Xianyi's documents. Emotion is carried entirely by verbs, imagery, and parallelism. This is the first red line — and the one AI breaks most often.

**How to trigger it**

```
帮我写第七届思源模拟联合国大会的邀请函，主题是"XXX"
帮我凝练一下下一届大会的主题，给几个候选
帮我写一份活动方案的第二部分"大会选题介绍、阐释及展望"
帮我把这份致辞改成蒙贤熠的文风
检查这份稿子像不像 MXY 写的
```

**You must provide the theme first.** The skill refuses to start without it — the theme determines every downstream choice of current events, committee arrangement, and value landing.

**What's inside**

```
write-official-document-like-mxy-jr/
├── SKILL.md              Main file: workflow, genre routing table, six hard rules
├── references/
│   ├── 01-写作能力.md     Theme triage, committee interlock logic, current-affairs research, nine-part skeleton
│   ├── 02-文风基因.md     Tone, syntax rhythm, imagery system, four-tier citation table, taboo list
│   ├── 03-历届主题与时事档案.md  Per-conference breakdowns of themes, committees, and event integration
│   └── 04-原文选段.md     Source excerpts: 3 addresses, 5 invitations, 2 proposal sections
└── scripts/
    └── style_check.py    Style linter: 14 metrics, scored output with per-item advice
```

**Built-in style linter**

Run it after drafting — 14 metrics, scored, with exactly what to fix:

```bash
python write-official-document-like-mxy-jr/scripts/style_check.py draft.md
```

Checks exclamation density, internet slang, four-character-idiom density, citation density, average sentence length, long-sentence ratio, passive-voice ratio, paragraph length, parallelism density, AI-tell banned words, signature closing, and byline.

The thresholds are not guesses — they were reverse-calibrated against Meng Xianyi's real documents:

| Sample | Score | Exit code |
|---|---|---|
| 2nd-conference secretary-general address (original) | 100 | 0 |
| 6th-conference proposal, "大会目的及意义" section | 94 | 0 |
| An AI-flavored negative sample | 62.5 | 1 |

* * *

## 🌟 About

This is the public skill collection of the Guangxi Siyuan Model United Nations Conference. The skills come from materials the organizing committee actually wrote and used — every conference proposal, invitation, and address was proven in a real event before being open-sourced.

Questions or suggestions are welcome in Issues / Discussions.

* * *

MIT License · free to use, modify, and redistribute
