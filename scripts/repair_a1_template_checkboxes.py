#!/usr/bin/env python3
"""One-time, hash-guarded repair of three baked selections in the blank A1 shell.

This edits the canonical background, never a worker PDF or generation overlay.
Every pixel outside the bounded checkbox interiors must remain unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pymupdf

SOURCE_SHA256 = '84a6526b9bb12af6a900a5e6b92d4e07cd053664413836d23731a00a55370f3c'
# PDF top-left points measured from the canonical raster shell. The border stays.
REPAIRS = ((0, (453.925, 379.675, 463.95, 389.7)),
           (0, (81.425, 654.425, 88.575, 661.825)),
           (2, (77.55, 419.55, 84.95, 426.95)))


def repair(source: Path, output: Path):
    original_mode = source.stat().st_mode & 0o777
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError('UNRECOGNIZED_TEMPLATE_VERSION')
    doc = pymupdf.open(stream=original, filetype='pdf')
    for number, coords in REPAIRS:
        rect = pymupdf.Rect(coords)
        pix = doc[number].get_pixmap(matrix=pymupdf.Matrix(8,8),clip=rect,alpha=False)
        pixels = np.frombuffer(pix.samples,dtype=np.uint8).reshape(-1,3)
        colors,counts = np.unique(pixels[pixels.min(1)>200],axis=0,return_counts=True)
        fill = tuple(float(x)/255 for x in colors[counts.argmax()])
        doc[number].add_redact_annot(rect,fill=fill,cross_out=False)
    for page in doc:
        page.apply_redactions(images=2,graphics=0,text=0)
    fixed = doc.tobytes(garbage=4,deflate=True)
    checks = []
    with pymupdf.open(stream=original,filetype='pdf') as before,pymupdf.open(stream=fixed,filetype='pdf') as after:
        for dpi in (144,300):
            scale=dpi/72
            for n in range(len(before)):
                a=before[n].get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
                b=after[n].get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
                x=np.frombuffer(a.samples,dtype=np.uint8).reshape(a.height,a.width,3)
                y=np.frombuffer(b.samples,dtype=np.uint8).reshape(b.height,b.width,3)
                changed=np.any(x!=y,axis=2)
                allowed=np.zeros(changed.shape,dtype=bool)
                for page,coords in REPAIRS:
                    if page==n:
                        r=pymupdf.Rect(coords)*scale
                        allowed[max(0,int(r.y0)-2):int(r.y1)+3,max(0,int(r.x0)-2):int(r.x1)+3]=True
                outside=int((changed & ~allowed).sum())
                if outside:raise ValueError('TEMPLATE_CHANGED_OUTSIDE_CHECKBOX_INTERIORS')
                checks.append({'page':n+1,'dpi':dpi,'outside_changed_pixels':outside})
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.template-',dir=output.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(fixed);f.flush();os.fsync(f.fileno())
        os.replace(name,output)
        output.chmod(original_mode)
    finally:Path(name).unlink(missing_ok=True)
    return {'source_sha256':SOURCE_SHA256,'output_sha256':hashlib.sha256(fixed).hexdigest(),
            'repairs':[{'page':n+1,'rect':list(rect)} for n,rect in REPAIRS], 'checks':checks}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    receipt=repair(args.source,args.output)
    args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
