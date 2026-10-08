"""按 PMC 2026 官方云数据服务逐篇获取许可开放的 PDF。"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent
ITEMS={
 'B01':('PMC3811145','10.1016/j.neuron.2013.07.051','神经与心理物理','自然触觉传入神经综述'),
 'B03':('PMC7738194','10.1088/1741-2560/6/6/066008','神经与心理物理','电与机械刺激心理物理'),
 'B04':('PMC9072403','10.1038/s41598-022-10708-9','神经与心理物理','电刺激感知与不耐受阈值'),
 'B07':('PMC3045309','10.1186/1743-0003-8-9','神经与心理物理','刺激模式与感知阈值'),
 'B08':('PMC4060858','10.1186/1743-0003-11-97','神经与心理物理','前臂位置与脉冲数辨认'),
 'C02':('PMC6023082','10.3390/bios8020031','电极皮肤界面','角质层阻抗模型综述'),
 'C04':('PMC9656728','10.3390/s22218510','电极皮肤界面','材料与含水量对接触阻抗'),
 'C05':('PMC8348734','10.3390/s21155210','电极皮肤界面','皮肤电极阻抗的时间演变'),
 'D01':('PMC4182789','10.1186/1743-0003-11-138','系统集成与供能','肌电与电触觉分时复用'),
 'D03':('PMC7857682','10.1126/sciadv.abe2943','系统集成与供能','早期自供能电触觉系统'),
 'D05':('PMC13360109','10.1002/advs.76616','系统集成与供能','自供能传感与电热触觉'),
}

def fetch(pair):
    id,(pmcid,doi,folder,slug)=pair
    target=BASE/folder/f'{id}_{slug}.pdf'
    if target.exists() and target.read_bytes()[:5]==b'%PDF-':return id,'已有',target.stat().st_size,''
    try:
        meta=None
        for version in (1,2,3):
            u=f'https://pmc-oa-opendata.s3.amazonaws.com/metadata/{pmcid}.{version}.json'
            r=requests.get(u,timeout=18)
            if r.status_code==200:
                meta=r.json()
                if meta.get('doi','').lower()==doi.lower() and meta.get('is_pmc_openaccess') and meta.get('pdf_url'):
                    break
                meta=None
        if not meta:return id,'无可复用开放PDF',pmcid,''
        s3=meta['pdf_url']
        url=s3.replace('s3://pmc-oa-opendata/','https://pmc-oa-opendata.s3.amazonaws.com/',1)
        r=requests.get(url,timeout=45)
        if r.status_code==200 and r.content[:5]==b'%PDF-' and len(r.content)>10000:
            target.write_bytes(r.content)
            return id,'保存',len(r.content),meta.get('license_code','')
        return id,'下载失败',r.status_code,r.headers.get('content-type','')
    except Exception as e:return id,'错误',str(e)[:80],''

with ThreadPoolExecutor(max_workers=5) as pool:
    for result in pool.map(fetch,ITEMS.items()):print(*result,sep='\t')
