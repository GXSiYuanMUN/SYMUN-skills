# 贡献指南

感谢关注本仓库。本仓库收集广西·思源模拟联合国大会在真实办会中打磨出来的技能。

## 仓库结构

```
SYMUN-skills/
├── skills/<skill-name>/          每个 Skill 一个独立目录
│   ├── SKILL.md                  必需：frontmatter + 指令正文
│   ├── references/               可选：按需加载的参考文档
│   ├── scripts/                  可选：可执行脚本
│   ├── assets/                   可选：模板与静态资源
│   └── LICENSE.txt               可选：技能专属许可
├── scripts/validate_skills.py    仓库级：规范校验（CI 调用）
└── .claude-plugin/marketplace.json  插件市场清单
```

**新增 Skill 时，请放在 `skills/` 目录下，目录名与 `SKILL.md` 里的 `name` 字段必须完全一致。**

## 提交前的自检

```bash
# 1. 规范校验（目录名、frontmatter、name 一致性、license、引用路径）
python scripts/validate_skills.py

# 2. 技能自带的脚本跑一遍
python skills/<skill-name>/scripts/<script>.py --help
```

两项都通过再提 PR。CI 会自动跑同样的检查。

## Agent Skills 规范要点

必填字段与约束：

| 字段 | 约束 |
|---|---|
| `name` | 1–64 字符，**仅小写字母、数字、连字符**，不可含空格与大写，必须与父目录名完全一致 |
| `description` | 1–1024 字符，需写明"什么场景该用"，便于 Agent 判断何时触发 |
| `license` | 可选，许可证名或指向仓库内文件的引用 |
| `metadata` | 可选，任意键值对 |

目录约定：

- `SKILL.md` 为必需文件
- `references/`、`scripts/`、`assets/` 为可选
- `references/` 建议只用一级，不要嵌套子目录链

## 写作规范

- **`SKILL.md` 正文控制在 300 行以内**。超过就拆进 `references/`，Agent 按需加载。
- **写祈使句**，不用第二人称（"应先确认主题" 而非 "你应该先确认主题"）。
- **不要在 `SKILL.md` 里堆重复信息**。细节放 `references/`，正文只留流程骨架与索引。
- **所有事实性内容标注来源**（年份、文件全称、数据出处）。

## 关于素材引用

本仓库的技能多以真实公文为蒸馏素材。若你的贡献涉及引用他人文本：

1. **必须标明原作者**，不得默认归于仓库所有者。
2. 引用仅供学习参考，正文须声明"模仿句法结构，不得复制句子"。
3. 涉及著作权归属的，在 `LICENSE` 中补充说明。

> 这一条不是形式主义。本仓库第一版曾误把他人的邀请函当作仓库所有者的作品收录，
> 推送前逐篇核实归属后才修正——公开仓库一旦发布，纠正成本远高于发布前。

## 提交信息

用中文或英文均可，格式参考 Conventional Commits：

```
feat: 新增 <skill-name> 技能
fix: 修正 <某处> 的引用路径
docs: 补充 <某文件> 的说明
refactor: 调整 <目录结构>
```

## 提问与建议

- Bug 与功能建议 → Issues
- 讨论与想法 → Discussions
- 想贡献新技能 → 先开 Issue 描述思路，避免重复劳动
