#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
像MXY.jr那样写公文 —— 风格自检脚本

用法:
    python style_check.py <稿件路径> [--json]

检测维度:
    1. 感叹号密度      —— 本技能作者原稿通篇为 0，硬红线
    2. 网络用语/口水词 —— 出现即扣分
    3. 四字格密度      —— 目标每 200 字 4-6 个
    4. 引证密度        —— 目标每千字 2-5 处
    5. 平均句长        —— 目标 28-55 字
    6. 长句占比        —— 目标 >= 25%
    7. 被动句占比      —— 目标 <= 8%
    8. 段落长度        —— 目标 3-8 句
    9. 三分/多项并列   —— 目标每 300 字至少 1 处
   10. 禁用词          —— AI 味/空话/翻译腔
   11. 结尾格式        —— 检验"吾等联合国之子民"等标志性收束
   12. 权威引证标记    —— 提示是否有未标注来源的引文

退出码: 0 = 通过(>=70分) ; 1 = 需修改
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 词表

NET_SLANG = [
    "绝绝子", "yyds", "破防", "内卷", "躺平", "emo", "666", "打卡", "绝子",
    "yyds了", "真的会谢", "芭比Q", "栓Q", "泰裤辣", "笑死",
    "无敌", "巨无霸", "yyds",
]

WATER_WORDS = [
    "非常好", "特别棒", "超级好", "十分十分", "简直是", "简直太",
    "非常非常", "极其", "无比", "更为重要", "至关重要且", "不言而喻",
]

# AI 味 / 翻译腔 / 公文套话
FORBIDDEN = [
    "首先", "其次", "最后，", "综上所述", "总而言之，综上",
    "Moreover", "Furthermore", "In conclusion", "It is worth noting",
    "值得注意的是", "不得不说", "总得来说", "简单来说", "换句话说",
    "众所周知", "不言而喻", "毋庸置疑", "众所周知，",
    "在当今社会", "在当今时代", "随着社会的发展", "随着时代的发展",
    "充分发挥", "切实加强", "深入贯彻落实", "扎实推进", "广泛开展",
    "具有重大、深远的意义", "具有重要意义", "深远的影响",
    "基于这一考虑", "做出决定", "不仅仅是一个", "不仅仅是一个",
    "不仅仅是", "这不仅是", "一个重要的方面", "需要指出的是",
    "引发广泛关注", "引发热议", "具有极高的", "极大地",
]

# 引证标记（用于统计引证密度）
QUOTE_RE = re.compile(r"[\u201c\u2018\"](.{4,}?)[\u201d\u2019\"]")

# 领导人/机构/文件引证标记
CITE_PATTERNS = [
    r"习近平", r"习近平总书记", r"党的二十大", r"二十届", r"全国人大",
    r"王毅", r"外交部", r"外交部发言人", r"联合国", r"秘书长",
    r"慕安会", r"慕尼黑安全会议", r"联大", r"第\s*\d+\s*届",
    r"《[^》]{4,}》", r"新华社", r"人民日报", r"中国政府网",
    r"安南", r"古特雷斯", r"两会", r"政府工作报告", r"规划的建议",
]

# 四字格：以 2~4 字为单位的并列短语，检测常见汉语成语式结构
FOUR_CHAR_RE = re.compile(
    r"[\u4e00-\u9fa5]{2,4}"
)

# 已知四字格白名单锚点（提高识别确定性）
FOUR_CHAR_ANCHORS = [
    "百年未有", "波诡云谲", "政治过硬", "素质全面", "举世瞩目", "气象万千",
    "承前启后", "继往开来", "行稳致远", "固本培元", "标本兼治", "踔厉奋发",
    "勇毅前行", "笃行不怠", "开拓进取", "求真务实", "凝心聚力", "奋发有为",
    "安危与共", "同舟共济", "休戚与共", "命运与共", "守望相助", "团结奋斗",
    "攻坚克难", "迎难而上", "主动作为", "开放包容", "求同存异", "合作共赢",
    "共商共建", "互联互通", "互利共赢", "共同发展", "全球治理", "全球南方",
    "发展共同体", "命运共同体",
]

# 三分/多项并列：顿号或逗号连接的 3 项及以上平行短语
# 本技能作者的排比常用逗号（"奔赴山海，追光逐焰，踏浪而行"）与顿号混用，两种都要识别
SANLI_DUN = re.compile(r"[\u4e00-\u9fa5]{2,10}(?:、[\u4e00-\u9fa5]{2,10}){2,}")
SANLI_DOU = re.compile(r"[\u4e00-\u9fa5]{2,8}(?:，[\u4e00-\u9fa5]{2,8}){2,}")

# 被动句标记
PASSIVE_RE = re.compile(r"被[^，。；：？！]{1,12}?(?:了|着|过)")

def split_sentences(text):
    """按中文句末标点切句，保留标点。分号视为句内分句，不切分。"""
    parts = re.split(r"(?<=[。！？!?\n])", text)
    return [p.strip() for p in parts if p.strip() and not p.strip().isdigit()]


def split_clauses(text):
    """按分号进一步切分，用于段落句数统计。"""
    parts = re.split(r"(?<=[；;。！？!?])", text)
    return [p.strip() for p in parts if p.strip() and not p.strip().isdigit()]


def split_paragraphs(text):
    """按空行分段，并剔除 Markdown 标题行。"""
    raw = re.split(r"\n\s*\n|\r\n\s*\r\n", text)
    out = []
    for p in raw:
        p = p.strip()
        if not p:
            continue
        if re.match(r"^#{1,6}\s", p):   # 标题行
            continue
        out.append(p)
    return out


def count_four_char(text):
    """保守估计四字格数量：统计候选 2-4 字连续汉字块中，形成语义单元的比例。"""
    # 简化为：统计含并列结构的四字候选 + 明确锚点
    anchors = sum(text.count(a) for a in FOUR_CHAR_ANCHORS if len(a) >= 4)
    # 统计 "X之X" "XX相X" "XX在X" 等典型四字构型
    patterns = re.findall(
        r"[\u4e00-\u9fa5]{2}(?:相|之|在|而|与|以|其)[\u4e00-\u9fa5]{1,2}", text
    )
    return anchors + len(patterns)


def detect_style(text, lines):
    """返回检测结果列表。"""
    results = []
    n_chars = len(re.sub(r"\s", "", text))
    if n_chars == 0:
        return [{"name": "文件", "status": "fail", "value": "文件为空", "advice": "检查文件路径"}]

    # 1. 感叹号
    excl = text.count("！") + text.count("!")
    r1 = excl / max(n_chars / 1000, 1)
    results.append({
        "name": "感叹号密度",
        "value": f"{excl} 个（{r1:.1f} 个/千字）",
        "status": "pass" if excl == 0 else ("warn" if excl <= 3 else "fail"),
        "advice": "本技能作者原稿通篇无感叹号。请改用动词、意象与排比承载情绪。" if excl else "符合",
    })

    # 2. 网络用语
    hits = [w for w in NET_SLANG if w in text]
    results.append({
        "name": "网络用语",
        "value": "、".join(hits) if hits else "无",
        "status": "pass" if not hits else "fail",
        "advice": "全部删除，改为书面表达。" if hits else "符合",
    })

    # 3. 口水词
    water = [w for w in WATER_WORDS if w in text]
    results.append({
        "name": "口水词/情绪外溢词",
        "value": "、".join(water) if water else "无",
        "status": "pass" if not water else ("warn" if len(water) <= 2 else "fail"),
        "advice": "改为具体动词或意象表达。" if water else "符合",
    })

    # 4. 四字格密度
    fc = count_four_char(text)
    per_200 = fc / max(n_chars / 200, 1)
    st = "pass" if 4 <= per_200 <= 9 else ("warn" if 2 <= per_200 < 12 else "fail")
    results.append({
        "name": "四字格密度",
        "value": f"约 {fc} 处（{per_200:.1f} 个/200字）",
        "status": st,
        "advice": "目标每 200 字 4-6 个。偏少则加节奏，偏多则显堆砌。" if st != "pass" else "符合",
    })

    # 5. 引证密度
    # 用位置去重计数，避免"习近平"与"习近平总书记"重复命中
    cite_positions = set()
    for pat in CITE_PATTERNS:
        for m in re.finditer(pat, text):
            cite_positions.add(m.start())
    cite_count = len(cite_positions)
    per_1000 = cite_count / max(n_chars / 1000, 1)
    # 短文本（<2000字）按绝对数判断，长文本按密度判断
    # 上限放宽至 12/千字：本技能作者的真实方案正文引证密度本就很高（约 12.8/千字）
    if n_chars < 2000:
        st = "pass" if 2 <= cite_count <= 14 else ("warn" if cite_count >= 1 else "fail")
    else:
        st = "pass" if 1.5 <= per_1000 <= 12 else ("warn" if per_1000 >= 0.8 else "fail")
    results.append({
        "name": "权威引证标记",
        "value": f"约 {cite_count} 处（{per_1000:.1f} 个/千字）",
        "status": st,
        "advice": "引证宜精不宜滥，且必须核实每处都标注了来源与年份。" if st != "pass" else "符合",
    })

    # 6. 引号使用（引证密度辅助）
    quotes = QUOTE_RE.findall(text)
    results.append({
        "name": "引文数量",
        "value": f"{len(quotes)} 处引号内容",
        "status": "pass" if len(quotes) <= 40 else "warn",
        "advice": "引文过多会稀释重点。" if len(quotes) > 40 else "符合",
    })

    # 7. 平均句长
    # 区间经真实原文校准：致辞类约 38 字，方案正文约 58 字，故上限放宽至 62
    sents = split_sentences(text)
    body = [s for s in sents if len(re.sub(r"\s", "", s)) >= 4]
    avg = sum(len(re.sub(r"\s", "", s)) for s in body) / max(len(body), 1)
    st = "pass" if 26 <= avg <= 62 else ("warn" if 16 <= avg <= 75 else "fail")
    results.append({
        "name": "平均句长",
        "value": f"{avg:.1f} 字（{len(body)} 句）",
        "status": st,
        "advice": "目标 26-62 字。致辞偏短（~38），方案正文偏长（~58）。过长则拆句，过短则加并列与意象。" if st != "pass" else "符合",
    })

    # 8. 长句占比（阈值 50 字，经第二届致辞原文校准）
    longs = [s for s in body if len(re.sub(r"\s", "", s)) >= 50]
    ratio = len(longs) / max(len(body), 1)
    st = "pass" if ratio >= 0.15 else ("warn" if ratio >= 0.08 else "fail")
    results.append({
        "name": "长句占比",
        "value": f"{ratio*100:.0f}%（{len(longs)}/{len(body)}，阈值 50 字）",
        "status": st,
        "advice": "本技能作者以长句铺陈、短句转折。长句占比过低说明碎句过多。" if st != "pass" else "符合",
    })

    # 9. 被动句
    pas = PASSIVE_RE.findall(text)
    p_ratio = len(pas) / max(len(body), 1)
    st = "pass" if p_ratio <= 0.08 else ("warn" if p_ratio <= 0.15 else "fail")
    results.append({
        "name": "被动句占比",
        "value": f"{p_ratio*100:.0f}%（{len(pas)} 处）",
        "status": st,
        "advice": "目标 <=8%。本技能作者多用主动句与使令句。" if st != "pass" else "符合",
    })

    # 10. 段落长度（按分句计）
    # 本技能作者有大量"独立成段的短句"（如"大家好。""2024年4月23日。"），属正常，
    # 因此只对过长段落（>9 句）告警，短段不扣分。
    paras = split_paragraphs(text)
    plens = [len(split_clauses(p)) for p in paras if len(p) > 30]
    if plens:
        bad = [n for n in plens if n > 9]
        st = "pass" if not bad else ("warn" if len(bad) <= len(plens) // 4 else "fail")
        results.append({
            "name": "段落长度",
            "value": f"平均 {sum(plens)/len(plens):.1f} 句/段（{len(plens)} 段，{len(bad)} 段超长）",
            "status": st,
            "advice": "目标每段 3-8 句。超过 9 句应拆分。短句独立成段是本技能作者的常用手法，不扣分。" if st != "pass" else "符合",
        })

    # 11. 三分并列
    sanli = SANLI_DUN.findall(text) + SANLI_DOU.findall(text)
    sl_per_300 = len(sanli) / max(n_chars / 300, 1)
    st = "pass" if sl_per_300 >= 1.0 else ("warn" if sl_per_300 >= 0.5 else "fail")
    results.append({
        "name": "多项并列（三分句式）",
        "value": f"约 {len(sanli)} 处（{sl_per_300:.1f} 处/300字）",
        "status": st,
        "advice": "本技能作者几乎每段都有三项以上的并列。补齐两项并列为三项。" if st != "pass" else "符合",
    })

    # 12. 禁用词
    bad_hits = []
    for w in FORBIDDEN:
        if w and w in text:
            bad_hits.append(w)
    bad_hits = sorted(set(bad_hits))
    st = "pass" if not bad_hits else ("warn" if len(bad_hits) <= 3 else "fail")
    results.append({
        "name": "禁用词（AI味/翻译腔/套话）",
        "value": "、".join(bad_hits[:12]) + ("…" if len(bad_hits) > 12 else "") if bad_hits else "无",
        "status": st,
        "advice": "逐项删除或改写为具体表述。" if bad_hits else "符合",
    })

    # 13. 结尾格式
    tail = text[-400:]
    closing_hits = [
        k for k in ["吾等联合国之子民", "为更美好之世界而联合", "敬请光临", "批评指正"]
        if k in tail
    ]
    st = "pass" if closing_hits else "warn"
    results.append({
        "name": "标志性收束",
        "value": "、".join(closing_hits) if closing_hits else "未检出",
        "status": st,
        "advice": "结尾宜含『吾等联合国之子民，为更美好之世界而联合』或『敬请光临』等标志性收束。" if st != "pass" else "符合",
    })

    # 14. 落款
    # 落款检查的是「职务 + 姓名 + 日期」的排版形式，不限定具体姓名
    sig = bool(re.search(r"大会秘书长|学术总监|外联总监|会务总监", text[-300:])) \
        or bool(re.search(r"\S{2,4}\s*[\r\n]+\s*\d{4}\s*年", text[-300:]))
    results.append({
        "name": "落款署名",
        "value": "检出" if sig else "未检出",
        "status": "pass" if sig else "warn",
        "advice": "致辞类文本末尾应有『大会秘书长  <姓名> + 日期』形式的落款。" if not sig else "符合",
    })

    return results


def score(results):
    """按维度加权打分。"""
    weight = {
        "感叹号密度": 10, "网络用语": 8, "口水词/情绪外溢词": 6,
        "四字格密度": 8, "权威引证标记": 10, "引文数量": 3,
        "平均句长": 8, "长句占比": 8, "被动句占比": 6,
        "段落长度": 7, "多项并列（三分句式）": 9, "禁用词（AI味/翻译腔/套话）": 12,
        "标志性收束": 3, "落款署名": 2,
    }
    total = 0.0
    for r in results:
        w = weight.get(r["name"], 5)
        total += w * {"pass": 1.0, "warn": 0.6, "fail": 0.15}.get(r["status"], 0.5)
    return round(total, 1)


def print_report(results, sc, path):
    icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
    print("=" * 62)
    print("像MXY.jr那样写公文 —— 风格自检报告")
    print("=" * 62)
    print(f"文件：{path}")
    print()
    for r in results:
        print(f"{icon[r['status']]} {r['name']}")
        print(f"    数值：{r['value']}")
        if r["status"] != "pass":
            print(f"    建议：{r['advice']}")
    print()
    print("-" * 62)
    grade = "优秀" if sc >= 85 else ("合格" if sc >= 70 else ("待改进" if sc >= 55 else "需重写"))
    print(f"综合评分：{sc} / 100  （{grade}）")
    print("-" * 62)
    if sc < 70:
        print("⚠️  请按上表建议逐项修改后重新运行本脚本。")
        print("   特别注意：感叹号必须为 0；所有引文必须已实际检索并标注来源。")
    else:
        print("✅ 通过。最后请人工通读一遍，检查三层咬合（主题—时代—青年）是否成立。")


def main():
    ap = argparse.ArgumentParser(description="像MXY.jr那样写公文 —— 风格自检")
    ap.add_argument("path", help="待检查的稿件文件路径")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"文件不存在：{p}", file=sys.stderr)
        sys.exit(2)

    text = p.read_text(encoding="utf-8", errors="ignore")
    results = detect_style(text, text.splitlines())
    sc = score(results)

    if args.json:
        print(json.dumps({
            "file": str(p),
            "score": sc,
            "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        print_report(results, sc, p)

    sys.exit(0 if sc >= 70 else 1)


if __name__ == "__main__":
    main()
