from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
META = ROOT / "检索元数据" / "筛选文献.json"
papers = json.loads(META.read_text(encoding="utf-8"))
raw = json.loads((ROOT / "检索元数据" / "OpenAlex原始记录.json").read_text(encoding="utf-8"))
types = {w["doi"].removeprefix("https://doi.org/").lower(): w.get("type") for w in raw if w.get("doi")}

EXCLUDE = {
    "10.37188/lam.2020.007": "同名文章的早期/重复元数据；以期刊正式 2021 DOI 为准",
    "10.1002/btm2.10445/v2/response1": "审稿回复，非论文",
    "10.1038/s41928-023-01115-7": "勘误，不作为独立研究论文",
    "10.1149/ma2021-01351133mtgabs": "会议摘要，无完整论文",
    "10.1002/advs.202270200": "同篇研究的封面/重复记录；以正式研究论文 DOI 为准",
}
YEAR = {
    "10.1016/j.mtphys.2021.100602": 2022,
    "10.1109/ojnano.2022.3218960": 2023,
    "10.1088/2631-7990/acfd69": 2024,
    "10.1002/aisy.202300070": 2024,
}
REVIEW = {
    "10.1038/s44460-026-00105-4",
    "10.1038/s41578-025-00877-0",
    "10.1002/sys3.70018",
    "10.1039/d4cs00413b",
    "10.1016/j.matt.2024.06.010",
    "10.1016/j.mtphys.2021.100602",
    "10.1109/ojnano.2022.3218960",
    "10.37188/lam.2021.004",
}
HAPTIC = {"10.1016/j.device.2024.100326"}
CORE = {
    "10.1038/s41586-019-1687-0", "10.1016/j.mtphys.2021.100602", "10.1039/d4cs00413b",
    "10.1016/j.matt.2024.06.010", "10.1038/s41578-025-00877-0", "10.1002/sys3.70018",
    "10.1038/s42256-022-00543-y", "10.1038/s41928-023-01074-z", "10.1126/sciadv.adq9575",
    "10.1126/sciadv.adt0318", "10.34133/cbsystems.0515", "10.1126/sciadv.ade2450",
    "10.1126/sciadv.abl6700", "10.1126/sciadv.adt6041", "10.1038/s41928-024-01189-x",
    "10.1126/sciadv.aed7673", "10.1109/ojnano.2022.3218960", "10.37188/lam.2021.004",
    "10.1038/s44460-026-00105-4", "10.1002/inf2.12079",
}
HTML_FULL_TEXT = {
    "10.1002/sys3.70018": "https://onlinelibrary.wiley.com/doi/10.1002/sys3.70018",
    "10.34133/cbsystems.0515": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13039521/",
    "10.1126/sciadv.aed7673": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13082325/",
}

retained = []
excluded_file = ROOT / "检索元数据" / "排除记录.json"
excluded = json.loads(excluded_file.read_text(encoding="utf-8")) if excluded_file.exists() else []
for p in papers:
    doi = p["doi"].lower()
    typ = types.get(doi)
    reason = EXCLUDE.get(doi)
    if not doi:
        reason = "无可核验 DOI；可能为会议或其他非正式发表记录"
    if typ in {"peer-review", "conference-abstract", "editorial", "posted-content", "preprint"}:
        reason = f"OpenAlex 类型为 {typ}，不是正式期刊论文"
    if p["title"].lower().startswith(("addendum:", "publisher correction:", "author response")):
        reason = "增补、勘误或审稿回复"
    if reason:
        if not any(item.get("doi") == doi and item.get("title") == p["title"] for item in excluded):
            excluded.append({"title": p["title"], "doi": doi, "reason": reason, "local_pdf": p.get("local_pdf")})
        continue
    p["year"] = YEAR.get(doi, p["year"])
    if doi in REVIEW:
        p["category"] = "综述与前瞻"
    if doi in HAPTIC:
        p["category"] = "触觉与电触觉"
    p["literature_type"] = "综述/前瞻" if p["category"] == "综述与前瞻" else "研究论文"
    if doi == "10.1038/s41928-024-01243-8":
        p["literature_type"] = "News & Views"
        p["category"] = "其他相关研究"
    p["priority"] = "核心" if doi in CORE else "拓展"
    if p.get("local_pdf"):
        old = ROOT / p["local_pdf"]
        if old.is_file():
            new = ROOT / p["category"] / old.name
            if old != new and not new.exists():
                old.rename(new)
                p["local_pdf"] = new.relative_to(ROOT).as_posix()
    retained.append(p)

retained.sort(key=lambda p: (p["category"], -p["year"], p["title"].casefold()))
META.write_text(json.dumps(retained, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "检索元数据" / "排除记录.json").write_text(json.dumps(excluded, ensure_ascii=False, indent=2), encoding="utf-8")

cats = ["综述与前瞻", "触觉与电触觉", "皮肤界面与生物电子", "系统集成", "自供能与能源", "其他相关研究"]
pdf_count = sum(bool(p.get("local_pdf")) for p in retained)
lines = [
    "# 于欣格课题组相关文献总索引",
    "",
    "检索与整理日期：2026-09-29。按本综述主题筛选的文献库，覆盖课题组及于欣格教授参与的相关期刊论文。此处的‘完整’指本库所收录文献均列出元数据和全文状态，并非该组全部研究产出的穷尽名录。",
    "",
    f"**收录 {len(retained)} 篇；已保存并验证 PDF {pdf_count} 篇；其余 {len(retained)-pdf_count} 篇提供 DOI/官方入口。**",
    "",
    "## 检索与收录口径",
    "",
    "- 起点：课题组[官方发表列表](https://yu-electronics.com/publications/)与[香港城市大学学术库](https://scholars.cityu.edu.hk/en/persons/xingeyu/)；以 OpenAlex 作者记录扩展检索并抽取结构化元数据，重点覆盖 2018—2026 年。",
    "- 主题：触觉与电触觉、皮肤界面/生物电子、系统集成、自供能、柔性器件基础及相关综述。题名没有 electrotactile 的工作也按其技术作用收录。共同作者论文不等同于课题组主导，具体贡献需阅读原文确认。",
    "- 年份：以期刊正式刊期年份为主；个别开放数据库采用在线发表年份，已对重点文章依期刊页面校正。",
    "- 全文：只保存期刊、PubMed Central 和高校机构库提供的公开 PDF；下载后检查 PDF 文件头与页数。无本地文件不等于论文不开放，可能是自动下载被限流或仅开放 HTML。PDF 的原始来源记录在 `检索元数据/筛选文献.json`。",
    "- 作者：以下按元数据中的署名顺序列出；新近条目中的英文缩写来自课题组发表列表。权威引用格式请以 DOI 所指向的正式期刊页面为准。",
    "- 分类：每篇只放一个主类，跨类别相关性请以题名、关键词和[研究脉络与精读建议](研究脉络与精读建议.md)交叉判断。",
    "",
    "## 分类概览",
    "",
    "| 类别 | 篇数 | 本地 PDF |",
    "|---|---:|---:|",
]
for cat in cats:
    group = [p for p in retained if p["category"] == cat]
    lines.append(f"| {cat} | {len(group)} | {sum(bool(p.get('local_pdf')) for p in group)} |")

for cat in cats:
    lines.extend(["", f"## {cat}", ""])
    for num, p in enumerate((p for p in retained if p["category"] == cat), 1):
        doi = p["doi"]
        official = "https://doi.org/" + doi if doi else p["official_url"]
        title = p["title"].replace("|", "\\|")
        authors = "; ".join(p["authors"])
        pdf = f"[本地 PDF]({p['local_pdf']})" if p.get("local_pdf") else "未获取 PDF；见官方入口"
        if not p.get("local_pdf") and doi in HTML_FULL_TEXT:
            pdf += f"；[开放 HTML 全文]({HTML_FULL_TEXT[doi]})"
        lines.extend([
            f"### {cat[:2]}-{num:03d} · {p['year']} · {title}",
            "",
            f"- 作者：{authors}",
            f"- 期刊：*{p['journal']}*；类型：{p['literature_type']}；优先级：{p['priority']}",
            f"- DOI：[{doi}]({official})；官方链接：[{official}]({official})",
            f"- 全文：{pdf}",
            "",
        ])

(ROOT / "literature_index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
print("Indexed", len(retained), "PDFs", pdf_count, "Excluded", len(excluded))
print(Counter(p["category"] for p in retained))
