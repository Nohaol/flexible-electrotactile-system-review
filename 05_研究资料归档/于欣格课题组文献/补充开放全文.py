from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
META = ROOT / "检索元数据" / "筛选文献.json"
RAW = json.loads((ROOT / "检索元数据" / "OpenAlex原始记录.json").read_text(encoding="utf-8"))
papers = json.loads(META.read_text(encoding="utf-8"))
works = {w["doi"].removeprefix("https://doi.org/").lower(): w for w in RAW if w.get("doi")}
session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (academic literature review; public OA copies only)"


def pdf_links_for(landing: str) -> list[str]:
    try:
        r = session.get(landing, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower() or "_sm.pdf" in href.lower() or "supp" in href.lower():
                continue
            url = urljoin(r.url, href)
            if "scholars.cityu.edu.hk/files/" in url:
                url = url.replace("scholars.cityu.edu.hk/files/", "scholars.cityu.edu.hk/ws/portalfiles/portal/")
            if url not in urls:
                urls.append(url)
        return urls[:3]
    except requests.RequestException:
        return []


def filename(p: dict) -> str:
    title = re.sub(r"[^\w\- ]+", "", p["title"])
    return str(p["year"]) + "_" + re.sub(r"\s+", "_", title)[:90] + ".pdf"


manual = {
    "10.37188/lam.2021.004": ("综述与前瞻/2021_Recent_progress_of_skin-integrated_electronics_for_intelligent_sensing.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/77675958/Li_et_al._2021_Light_Advanced_Manufacturing_Recent_progress_of_skin_integrated_electronics_for_intelligent_sensing.pdf"),
    "10.1109/ojnano.2022.3218960": ("综述与前瞻/2023_Recent_Advances_in_Materials_Designs_and_Applications_of_Skin_Electronics.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/160270650/123032917.pdf"),
    "10.1016/j.device.2024.100326": ("触觉与电触觉/2024_Multiscale_haptic_interfaces_for_metaverse.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/225726264/221434755.pdf"),
    "10.1126/sciadv.adt0318": ("触觉与电触觉/2025_Self-powered_electrotactile_textile_haptic_glove.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/287783004/279312888.pdf"),
    "10.1126/sciadv.adq9575": ("触觉与电触觉/2024_A_fully_integrated_breathable_haptic_textile.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/255175132/253404237.pdf"),
    "10.1126/sciadv.ade2450": ("触觉与电触觉/2022_Touch_IoT_enabled_by_wireless_self-sensing.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/146244371/129829429.pdf"),
    "10.1038/s41928-023-01074-z": ("触觉与电触觉/2023_A_skin-integrated_multimodal_haptic_interface.pdf", "https://scholars.cityu.edu.hk/ws/portalfiles/portal/511544116/180189276.pdf"),
}

for i, p in enumerate(papers, 1):
    doi = p["doi"].lower()
    if doi in manual and (ROOT / manual[doi][0]).exists():
        p["local_pdf"], p["pdf_source"] = manual[doi]
        continue
    if p.get("local_pdf"):
        continue
    w = works.get(doi)
    if not w:
        continue
    candidates = []
    for loc in w.get("locations") or []:
        if not loc.get("is_oa"):
            continue
        landing = loc.get("landing_page_url") or ""
        if "pmc.ncbi.nlm.nih.gov" in landing or "www.ncbi.nlm.nih.gov/pmc" in landing:
            candidates.extend(pdf_links_for(landing.replace("www.ncbi.nlm.nih.gov/pmc", "pmc.ncbi.nlm.nih.gov")))
        elif "scholars.cityu.edu.hk" in landing or "hdl.handle.net/2031/" in landing:
            candidates.extend(pdf_links_for(landing))
        pdf_url = loc.get("pdf_url")
        if pdf_url and ("scholars.cityu.edu.hk" in pdf_url or "pmc.ncbi.nlm.nih.gov" in pdf_url):
            candidates.append(pdf_url.replace("scholars.cityu.edu.hk/files/", "scholars.cityu.edu.hk/ws/portalfiles/portal/"))
    for url in dict.fromkeys(candidates):
        try:
            r = session.get(url, timeout=25)
            if r.status_code != 200 or not r.content.startswith(b"%PDF") or len(r.content) < 10000:
                continue
            path = ROOT / p["category"] / filename(p)
            path.write_bytes(r.content)
            info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=10)
            match = re.search(r"(?m)^Pages:\s*(\d+)", info.stdout)
            if not match or int(match.group(1)) < 2:
                path.unlink(missing_ok=True)
                continue
            p["local_pdf"] = path.relative_to(ROOT).as_posix()
            p["pdf_source"] = url
            p["pages"] = int(match.group(1))
            print(f"PDF {i}/{len(papers)} {p['title'][:65]}", flush=True)
            break
        except (requests.RequestException, OSError, subprocess.TimeoutExpired):
            continue
    if i % 15 == 0:
        META.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")

META.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
print("Total PDFs", sum(bool(p.get("local_pdf")) for p in papers), flush=True)
