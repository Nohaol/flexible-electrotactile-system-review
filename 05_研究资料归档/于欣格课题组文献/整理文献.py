from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
RAW = json.loads((ROOT / "检索元数据" / "OpenAlex原始记录.json").read_text(encoding="utf-8"))

CATEGORIES = ["综述与前瞻", "触觉与电触觉", "皮肤界面与生物电子", "系统集成", "自供能与能源", "其他相关研究"]
for category in CATEGORIES:
    (ROOT / category).mkdir(exist_ok=True)
(ROOT / "检索元数据").mkdir(exist_ok=True)

REVIEW_TERMS = ["review", "recent advances", "recent progress", "progress on", "roadmap", "perspective", "outlook", "advances in materials for haptic", "device design principles", "multilayer flexible electronics", "bioelectronics for electrical stimulation", "self-powered skin electronics for energy"]
HAPTIC_TERMS = ["haptic", "electrotactile", "tactile information", "tactile feedback", "tactile perception", "mechanoreceptor", "neuromorphic system for tactile"]
SYSTEM_TERMS = ["fully integrated", "integrated bioelectronics", "closed-loop", "closed loop", "wireless human-machine", "wireless human machine", "touch iot", "system for", "system as", "multifunctional integrated", "monolithically integrated", "three-dimensional integrated"]
SKIN_TERMS = ["skin-integrated", "skin-interfaced", "skin electronics", "epidermal", "bioelectronic", "wearable", "soft electronic", "stretchable", "flexible", "skin-conformable", "liquid metal", "interface", "skin-like"]
POWER_TERMS = ["self-powered", "self-sustainable", "energy harvesting", "triboelectric", "nanogenerator", "battery-free", "wireless power", "sweat-activated batter", "biofuel cell", "energy supplier"]
OTHER_TERMS = ["soft robot", "3d print", "thermal management", "radiative cooling", "permeable", "breathable", "sensor", "electrochemical transistor"]

EXCLUDE_TERMS = ["publisher correction", "corrigendum", "erratum", "addendum", "retirement", "perovskite solar", "gas sensors based on organic", "infectious respiratory diseases", "rapid diagnosis of covid", "sars-cov-2 by flexible"]


def category_for(title: str) -> str | None:
    t = title.casefold()
    if any(k in t for k in EXCLUDE_TERMS):
        return None
    if any(k in t for k in REVIEW_TERMS):
        # Exclude remotely related review topics.
        if any(k in t for k in ["photodetector", "gas sensors", "coronavirus", "perovskite", "uric acid detection", "blood pressure", "drug delivery", "thermal management"]):
            return None
        return CATEGORIES[0]
    if any(k in t for k in HAPTIC_TERMS):
        return CATEGORIES[1]
    if any(k in t for k in SYSTEM_TERMS):
        return CATEGORIES[3]
    if any(k in t for k in POWER_TERMS):
        return CATEGORIES[4]
    if any(k in t for k in SKIN_TERMS):
        return CATEGORIES[2]
    if any(k in t for k in OTHER_TERMS):
        return CATEGORIES[5]
    return None


def clean_title(s: str) -> str:
    return s.replace("�\\", "-").replace("�C", "-").replace("‑", "-").replace("–", "-").strip()


def filename(p: dict) -> str:
    title = re.sub(r'[^\w\- ]+', '', clean_title(p["title"]), flags=re.UNICODE)
    title = re.sub(r'\s+', '_', title)[:90]
    return f'{p["year"]}_{title}.pdf'


def oa_candidates(work: dict) -> list[str]:
    locations = [work.get("best_oa_location")] + (work.get("locations") or [])
    urls = []
    for loc in locations:
        if not loc or not loc.get("is_oa") or not loc.get("pdf_url"):
            continue
        url = loc["pdf_url"]
        url = url.replace("https://scholars.cityu.edu.hk/files/", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/")
        host = urlparse(url).hostname or ""
        if any(bad in host for bad in ["researchgate.net", "sci-hub", "researchsquare.com"]):
            continue
        if url not in urls:
            urls.append(url)
    # Prefer institutional repository over publisher pages prone to automated access blocks.
    urls.sort(key=lambda u: (0 if "scholars.cityu.edu.hk" in u else 1 if "pmc.ncbi.nlm.nih.gov" in u else 2))
    return urls


def make_paper(work: dict) -> dict:
    source = (work.get("primary_location") or {}).get("source") or {}
    authors = [a["author"]["display_name"] for a in work.get("authorships", []) if a.get("author")]
    return {
        "title": clean_title(work["display_name"]),
        "year": work["publication_year"],
        "journal": source.get("display_name") or "待核验",
        "authors": authors,
        "doi": (work.get("doi") or "").removeprefix("https://doi.org/"),
        "official_url": work.get("doi") or work.get("id"),
        "category": category_for(work["display_name"]),
        "oa_status": work.get("open_access", {}).get("oa_status", "unknown"),
        "pdf_candidates": oa_candidates(work),
        "openalex_id": work.get("id"),
        "source": "OpenAlex; 课题组官网交叉核对",
    }


papers = [make_paper(w) for w in RAW if category_for(w["display_name"]) and w["type"] not in {"posted-content", "preprint"}]
papers = [p for p in papers if p["year"] <= 2026]
by_doi = {p["doi"].lower(): p for p in papers if p["doi"]}

# Newer group-site papers not yet associated with the main OpenAlex author record.
new_papers = [
    ("Deformable materials and structures in wearable haptic interfaces", "Nature Reviews Materials", 2026, "Z. Chen; Y. Huang; B. Zhang; D. Sun; X. Yu", "10.1038/s41578-025-00877-0", "综述与前瞻"),
    ("Recent Advances in Cutaneous Haptic Interfaces: A Review", "SmartSys", 2026, "X. Li; Y. Guo; C. Li; Y. Zhang; Y. Zheng; R. Wang; X. Yu; W. Ding; Q. Tong", "10.1002/sys3.70018", "综述与前瞻"),
    ("AI-powered closed-loop wearable bioelectronics for personalized and autonomous healthcare", "Nature Sensors", 2026, "B. Gao; Z. Ge; X. Sun; B. Lin; Y. Gao; J. Min; Q. Zhang; J. A. Rogers; X. Yu; W. Gao; C. T. Lim", "10.1038/s44460-026-00105-4", "综述与前瞻"),
    ("Wearable Fabric Electrotactile System with Stimulation-Inhibition Electrode Units", "Cyborg and Bionic Systems", 2026, "H. Yao; D. Li; W. Zhang; Q. Xiong; Y. Luo; C. Lin; J. Wang; J. Liu; M. Tan; X. Xu; Y. Ma; Y. Lin; Q. Hu; T. Huang; L. Shu; L. Wei; X. Yu; X. Xu", "10.34133/cbsystems.0515", "触觉与电触觉"),
    ("Drawn-on-skin electronic tattoo as a closed-loop sensing-stimulation system for the muscles", "Science Advances", 2026, "Y. Huang; Z. Chen; J. Zhou; H. Jia; L. Chow; Y. Zhou; S. Jia; B. Zhang; F. Ershad; S. Patel; C. K. Yiu; Y. Gao; Q. Zhang; X. Huang; J. Li; K. Yao; G. Zhao; P. Chen; H. Peng; D. Sun; C. Yu; X. Yu", "10.1126/sciadv.aed7673", "系统集成"),
    ("An All-in-One-Integrated Self-Powered Wearable Sensing System for Multimodal Health Monitoring", "ACS Nano", 2026, "J. Liang; X. Cai; L. Huang; L. Chen; F. Tan; J. Qiu; Y. Zhang; W. Yan; W. Lin; G. Zhong; R. Ye; J. Zhao; X. Yu; C. Tan", "10.1021/acsnano.5c17767", "自供能与能源"),
]

session = requests.Session()
session.headers.update({"User-Agent": "Academic bibliography for personal research (contact via CityUHK repository)", "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.5"})

for title, journal, year, authors, doi, category in new_papers:
    if doi and doi.lower() in by_doi:
        continue
    if any(p["title"].lower() == title.lower() for p in papers):
        continue
    papers.append({"title": title, "year": year, "journal": journal, "authors": authors.split("; "), "doi": doi,
                   "official_url": "https://doi.org/" + doi if doi else "https://yu-electronics.com/publications/",
                   "category": category, "oa_status": "待核验", "pdf_candidates": [], "openalex_id": None,
                   "source": "课题组官网（新近文献；元数据待二次核验）"})

papers.sort(key=lambda p: (-p["year"], p["title"].casefold()))
(ROOT / "检索元数据" / "筛选文献.json").write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
print("Selected:", len(papers), {c: sum(p["category"] == c for p in papers) for c in CATEGORIES}, flush=True)

# Download only locations identified as OA by OpenAlex and hosted by journal/repository.
for idx, p in enumerate(papers, 1):
    dest = ROOT / p["category"] / filename(p)
    if dest.exists():
        p["local_pdf"] = str(dest.relative_to(ROOT)).replace("\\", "/")
        continue
    for url in p["pdf_candidates"]:
        try:
            response = session.get(url, timeout=22)
            if response.status_code != 200 or not response.content.startswith(b"%PDF") or len(response.content) < 10000:
                continue
            dest.write_bytes(response.content)
            try:
                info = subprocess.run(["pdfinfo", str(dest)], capture_output=True, text=True, timeout=12)
                pages = int(re.search(r"(?m)^Pages:\s*(\d+)", info.stdout).group(1))
                if pages < 2:
                    dest.unlink(missing_ok=True)
                    continue
            except Exception:
                dest.unlink(missing_ok=True)
                continue
            p["local_pdf"] = str(dest.relative_to(ROOT)).replace("\\", "/")
            p["pdf_source"] = url
            p["pages"] = pages
            print(f"PDF {idx}/{len(papers)} {p['year']} {p['title'][:55]} ({pages} p)", flush=True)
            break
        except (requests.RequestException, OSError):
            continue
    if idx % 15 == 0:
        (ROOT / "检索元数据" / "筛选文献.json").write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")

(ROOT / "检索元数据" / "筛选文献.json").write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
print("Downloaded:", sum("local_pdf" in p for p in papers), flush=True)
