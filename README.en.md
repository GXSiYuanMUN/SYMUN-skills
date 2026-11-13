# SYMUN Skills

#### Public skill collection from Guangxi Siyuan Model United Nations Conference

Every Skill here is a structured instruction set that agents can load directly, following the [Agent Skills open standard](https://openagentskills.dev/docs/specification). It works in Claude Code, Codex, CodeBuddy, Cursor, and any other tool that supports the standard.

* * *

## 📋 Contents

| Name | One-liner | Docs |
|---|---|---|
| **write-official-document-like-mxy-jr** (Chinese display name: 像MXY.jr那样写公文.1.0) | Distills Meng Xianyi's (MXY.jr) official-document writing ability and style across six consecutive Siyuan MUN conferences — for invitations, secretary-general addresses, event proposals, and background papers | [Details](#-write-official-document-like-mxy-jr) |
| **workbuddy-c-drive-friendly** (Chinese display name: WorkBuddy C 盘友好版.1.0) | Read-only disk audit, then robocopy plus an NTFS directory junction (`mklink /J`) to move WorkBuddy's hard-coded runtime data off the system drive — original path unchanged, one-command rollback | [Details](#-workbuddy-c-drive-friendlyworkbuddy-c-盘友好版10) |

> This repository is primarily about conference skills, but also carries **agent productivity tools** that have been proven in real events and real office work.

* * *

## 📦 Installation

In any Agent Skills-compatible tool (Claude Code, Codex, etc.), just say:

```
帮我安装这个 skill：https://github.com/GXSiYuanMUN/SYMUN-skills/tree/main/skills/write-official-document-like-mxy-jr
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
# copy the skills/write-official-document-like-mxy-jr directory into .claude/skills/ or ~/.claude/skills/
```

* * *

## 🗂 Repository structure

```
SYMUN-skills/
├── skills/                          one directory per skill
│   ├── write-official-document-like-mxy-jr/
│   │   ├── SKILL.md                 required: frontmatter + instructions
│   │   ├── references/              docs loaded on demand
│   │   ├── scripts/                 executable scripts
│   │   └── LICENSE.txt
│   └── workbuddy-c-drive-friendly/
│       ├── SKILL.md
│       ├── references/              decision guide, layout, pitfalls, case study
│       ├── scripts/                 diagnose / make_bat / list_automations
│       └── LICENSE.txt
├── scripts/validate_skills.py       repo-level: spec validation (called by CI)
├── .claude-plugin/marketplace.json  plugin marketplace manifest
├── .github/                         CI, issue and PR templates
├── CONTRIBUTING.md                  contribution guide (incl. attribution rules)
├── CHANGELOG.md                    changelog
└── LICENSE                          MIT
```

**Adding a skill**: put it under `skills/`; the directory name must exactly match the `name` field in its `SKILL.md`. Run `python scripts/validate_skills.py` before committing.

* * *

## ✨ Skills

### ✍️ write-official-document-like-mxy-jr

> *"愿吾等联合国之子民，为更美好之世界而联合。"*

**It solves exactly one thing: making event proposals, invitations, and addresses read the way Meng Xianyi writes them.**

This is not a template. It decomposes the stable techniques behind the Siyuan MUN conference documents into something an agent can apply.

**On source material**: every sample included here was written by the author of this skill — the invitations and secretary-general addresses of the 2nd, 3rd, 4th, and 6th conferences, plus the event proposals of the 3rd through 6th. The 5th conference's invitation and address were written by that conference's secretary-general — **not the author's work, and excluded here** (the 5th conference's *proposal* was the author's, so its theme development and committee rationale remain valid samples).

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
python skills/write-official-document-like-mxy-jr/scripts/style_check.py draft.md
```

Checks exclamation density, internet slang, four-character-idiom density, citation density, average sentence length, long-sentence ratio, passive-voice ratio, paragraph length, parallelism density, AI-tell banned words, signature closing, and byline.

The thresholds are not guesses — they were reverse-calibrated against Meng Xianyi's real documents:

| Sample | Score | Exit code |
|---|---|---|
| 2nd-conference secretary-general address (original) | 100 | 0 |
| 6th-conference proposal, "大会目的及意义" section | 94 | 0 |
| An AI-flavored negative sample | 62.5 | 1 |

* * *

### 🛠️ workbuddy-c-drive-friendly (WorkBuddy C 盘友好版.1.0)

> *"Don't change the path. Change where it lands."*

**It solves one concrete problem: WorkBuddy / CodeBuddy slowly eats the C drive, and there is no setting anywhere to change its data directory.**

WorkBuddy hard-codes everything into `C:\Users\<you>\.workbuddy` — skills, memory, automation database, Python/Node runtimes, browser profiles. Long-term use pushes it into several GB; add `%LOCALAPPDATA%\ms-playwright` (browser kernels, ~1.4 GB) and the system drive is in trouble.

The approach: **move the data, leave a "portal" behind.**

```
Before:  C:\Users\<you>\.workbuddy\        real data (occupying C:)
After:   C:\Users\<you>\.workbuddy\  ══►  E:\FutureWay\_runtime\workbuddy\   ← real data
         (a directory junction — takes almost no space itself)
```

The program keeps reading and writing the C: path; Windows transparently resolves it to the new drive. **Path unchanged → no config edits, no broken history index, one command to roll back.**

**Three steps, fully reversible**

1. **Audit** (read-only, instant): `python scripts/diagnose.py` — free space per drive, whether the runtime is already a junction, which directories are worth moving, which workspaces sit on the system drive
2. **Generate the cutover scripts**: `python scripts/make_bat.py --pair "src::dst" ...` — four scripts generated from your real paths, never hand-written
3. **A human runs the cutover**: fully quit the app, then double-click `2_cutover.bat`; every directory must print `PASS`. `3_cleanup.bat` runs last and demands a typed `YES`

| Script | Purpose | Deletes anything? |
|---|---|---|
| `1_copy.bat` | First full copy + diff report | No |
| `2_cutover.bat` | Incremental sync → rename original → create junction → verify each; auto-rollback on failure | No |
| `3_cleanup.bat` | Delete the old copy, after verifying the junction is in place | **Yes** (the only one) |
| `9_rollback.bat` | Remove junction → restore original name; new-drive data untouched | No |

**Why the cutover is not delegated to the agent**

The agent itself usually runs from inside that data directory. Rewriting your own data directory while the process is live leaves a mixed state where old handles point at the old path and new processes point at the new one. So a human performs this step; the scripts put the guard rails up front.

**Three hard constraints (learned the hard way)**

- The target drive must be a **fixed disk** — never a USB stick, external drive, or network share. Losing the drive loses everything
- Detect junctions with `os.readlink()`, **not `os.path.islink()`** — the latter returns `False` for Windows junctions and will make you conclude the junction was lost
- **Relocation stops the bleeding, it does not cure it**: after moving 6.2 GB off C:, free space only recovered from 1.2 GB to 2.0 GB — Windows updates and other software ate the difference. It fixes one app's long-term growth, not a full-disk cleanup

**A related confusion it also settles**

"All my automations disappeared after the upgrade" is almost never true. Automation definitions live in the `automations` table of `workbuddy.db` and are bound to a working directory via `cwds[0]`; **if the workspace you have open is not in that task's `cwds`, the list is simply empty**. `scripts/list_automations.py` groups every task by workspace and checks whether its run archive is present.

**Measured on real data**

- 19,138 directories / 84,711 files / 4.645 GB — first copy took **1 min 24 s**
- Survived a version upgrade afterwards; the junction was untouched and the new version's own SQLite migrations landed on the new drive
- The four scripts were run end to end in a sandbox: copy → cutover → rollback → cleanup, including the safety valve that refuses to clean up when the source is not a junction

→ [SKILL.md](skills/workbuddy-c-drive-friendly/SKILL.md) · [Case study with post-migration review](skills/workbuddy-c-drive-friendly/references/case-study.md) · [12 real pitfalls](skills/workbuddy-c-drive-friendly/references/pitfalls.md)

* * *

## 🌟 About

This is the public skill collection of the Guangxi Siyuan Model United Nations Conference. The skills come from materials the organizing committee actually wrote and used — every conference proposal, invitation, and address was proven in a real event before being open-sourced.

Questions or suggestions are welcome in Issues / Discussions.

* * *

MIT License · free to use, modify, and redistribute
