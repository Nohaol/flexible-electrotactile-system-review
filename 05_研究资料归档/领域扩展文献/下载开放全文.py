"""只尝试期刊或高校机构库的公开 PDF；验证魔数后保存。"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent
ITEMS={
 'A05':('引言背景与综述','https://www.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2024.1406923/pdf','电触觉显示分类与挑战'),
 'A06':('系统集成与供能','https://engineering.purdue.edu/~hongtan/pubs/PDFfiles/J78_Lin-etal_SciAdv2022.pdf','超分辨率可穿戴电触觉系统'),
 'B04':('神经与心理物理','https://www.nature.com/articles/s41598-022-10708-9.pdf','电刺激感知与不耐受阈值'),
 'C01':('电极皮肤界面','https://upcommons.upc.edu/server/api/core/bitstreams/33b8e40a-946c-417a-a2ad-356fb9fbe434/content','皮肤阻抗频谱经典实验'),
 'C02':('电极皮肤界面','https://www.mdpi.com/2079-6374/8/2/31/pdf','角质层阻抗模型综述'),
 'C03':('电极皮肤界面','https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0125609&type=printable','经皮电刺激动态阻抗模型'),
 'C04':('电极皮肤界面','https://www.mdpi.com/1424-8220/22/21/8510/pdf','材料与含水量对接触阻抗'),
 'C05':('电极皮肤界面','https://www.mdpi.com/1424-8220/21/15/5210/pdf','皮肤电极阻抗的时间演变'),
 'D01':('系统集成与供能','https://jneuroengrehab.biomedcentral.com/counter/pdf/10.1186/1743-0003-11-138.pdf','肌电与电触觉分时复用'),
 'D02':('系统集成与供能','https://www.nature.com/articles/s41598-023-30545-8.pdf','便携多通道刺激驱动'),
}

def fetch(pair):
    id,(folder,url,slug)=pair
    path=BASE/folder/f'{id}_{slug}.pdf'
    try:
        r=requests.get(url,timeout=30,headers={'User-Agent':'Mozilla/5.0'},allow_redirects=True)
        if r.status_code==200 and r.content[:5]==b'%PDF-' and len(r.content)>10000:
            path.write_bytes(r.content)
            return id,'保存',len(r.content),r.url
        return id,'未取得',r.status_code,r.headers.get('content-type','')
    except Exception as e:return id,'失败',str(e)[:90],''

with ThreadPoolExecutor(max_workers=5) as pool:
    for result in pool.map(fetch,ITEMS.items()):print(*result,sep='\t')
