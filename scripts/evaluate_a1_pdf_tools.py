"""Local research harness for canonical template tools; never employee artifacts.
Install optional evaluation packages into runtime/portal/pdf-tool-evaluation/packages.
Run with the repository venv from its root. Results are single-run diagnostics,
not a production QA gate or a claim of cross-engine pixel identity.
"""
from pathlib import Path
import sys, json, hashlib, time, subprocess, importlib.metadata, os
os.umask(0o077)
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/portal/pdf-tool-evaluation'
OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
OUT.chmod(0o700)
sys.path.insert(0,str(OUT/'packages'))
import pymupdf, pypdf, pdfplumber, pypdfium2
import numpy as np
from PIL import Image
from reportlab.pdfgen import canvas

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# A synthetic vector reference provides known geometry, independent of any employee PDF.
c=canvas.Canvas(str(OUT/'synthetic.pdf'),pagesize=(595.2,841.92))
c.rect(100,200,10,10);c.drawString(80,700,'SYNTHETIC GEOMETRY');c.showPage();c.save()
(OUT/'committed-template.pdf').write_bytes(subprocess.check_output(['git','show','HEAD:templates/a1_background.pdf']))
results={'versions':{n:importlib.metadata.version(n) for n in ['pymupdf','pypdf','pdfplumber','pdfminer.six','pypdfium2']},'ghostscript':subprocess.check_output(['gs','--version'],text=True).strip(),'documents':{}}
for label,path in [('canonical',ROOT/'templates/a1_background.pdf'),('committed_baseline',OUT/'committed-template.pdf'),('synthetic',OUT/'synthetic.pdf')]:
 r={'sha256':sha(path),'size_bytes':path.stat().st_size};results['documents'][label]=r
 t=time.perf_counter()
 with pymupdf.open(path) as d:
  r['pymupdf']=[{'size':list(p.rect),'text_chars':len(p.get_text()),'images':len(p.get_images()),'vectors':len(p.get_drawings()),'widgets':len(list(p.widgets() or []))} for p in d]
  if label=='synthetic':r['synthetic_top_left_rect']=list(d[0].get_drawings()[0]['rect'])
 r['pymupdf_inspect_ms']=(time.perf_counter()-t)*1000
 t=time.perf_counter();reader=pypdf.PdfReader(path)
 r['pypdf']=[{'size':list(map(float,p.mediabox)),'text_chars':len(p.extract_text() or '')} for p in reader.pages]
 r['pypdf_inspect_ms']=(time.perf_counter()-t)*1000
 t=time.perf_counter()
 with pdfplumber.open(path) as d:
  r['pdfplumber']=[{'text_chars':len(p.extract_text() or ''),'images':len(p.images),'rectangles':len(p.rects),'lines':len(p.lines)} for p in d.pages]
  if label=='synthetic':r['synthetic_bottom_left_rect']=[d.pages[0].rects[0][k] for k in ['x0','y0','x1','y1']]
 r['pdfplumber_inspect_ms']=(time.perf_counter()-t)*1000
 if label!='canonical':continue
 r['renders']={}
 for dpi in [144,300]:
  record={'dpi':dpi};r['renders'][str(dpi)]=record
  t=time.perf_counter()
  with pymupdf.open(path) as d:
   for i,p in enumerate(d):p.get_pixmap(dpi=dpi,colorspace=pymupdf.csRGB,alpha=False).save(OUT/f'mupdf-{dpi}-{i+1}.png')
  record['mupdf_ms']=(time.perf_counter()-t)*1000
  t=time.perf_counter()
  d=pypdfium2.PdfDocument(path)
  for i in range(len(d)):
   page=d[i];bitmap=page.render(scale=dpi/72);bitmap.to_pil().convert('RGB').save(OUT/f'pdfium-{dpi}-{i+1}.png');bitmap.close();page.close()
  d.close();record['pdfium_ms']=(time.perf_counter()-t)*1000
  t=time.perf_counter()
  subprocess.run(['gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=png16m',f'-r{dpi}',f'-sOutputFile={OUT}/gs-{dpi}-%d.png',str(path)],check=True,timeout=60)
  record['gs_ms']=(time.perf_counter()-t)*1000
  record['pages']=[]
  for i in range(1,4):
   images={engine:np.asarray(Image.open(OUT/f'{engine}-{dpi}-{i}.png').convert('RGB')) for engine in ['mupdf','pdfium','gs']}
   row={'page':i,'shapes':{e:list(a.shape) for e,a in images.items()}}
   row['equal_canvas_pixel_mae']={}
   for e in ['pdfium','gs']:
    a,b=images['mupdf'],images[e]
    row['equal_canvas_pixel_mae'][e]=float(np.abs(a.astype(float)-b).mean()) if a.shape==b.shape else None
   record['pages'].append(row)
assert results['documents']['synthetic']['synthetic_bottom_left_rect']==[100,200,110,210]
rect=results['documents']['synthetic']['synthetic_top_left_rect']
assert max(abs(a-b) for a,b in zip(rect,[100,631.92,110,641.92]))<0.001
assert sha(ROOT/'templates/a1_background.pdf')==results['documents']['canonical']['sha256']
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
