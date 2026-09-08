"""One-time shell repair using original vector geometry, never employee values."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pymupdf


def restore(source: Path, output: Path, reference: Path):
    data = source.read_bytes()
    ref = json.loads(reference.read_text())
    if hashlib.sha256(data).hexdigest() != ref['repair_input_sha256']:
        raise ValueError('UNRECOGNIZED_BACKGROUND')
    with pymupdf.open(stream=data, filetype='pdf') as doc:
        for cfg in ref['checkboxes'].values():
            if cfg['previous_border']:
                rect = pymupdf.Rect(cfg['previous_border']) + (-.5, -.5, .5, .5)
                doc[cfg['page']].add_redact_annot(rect, fill=(1, 1, 1), cross_out=False)
        for page in doc:
            page.apply_redactions(images=2, graphics=0, text=0)
        for cfg in ref['checkboxes'].values():
            doc[cfg['page']].draw_rect(cfg['rect'], color=cfg['color'],
                                       width=cfg['line_width'], overlay=True)
        fixed = doc.tobytes(garbage=4, deflate=True)
    checks = []
    with pymupdf.open(stream=data, filetype='pdf') as before, pymupdf.open(stream=fixed, filetype='pdf') as after:
        for page in range(len(before)):
            a = before[page].get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
            b = after[page].get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
            x = np.frombuffer(a.samples, np.uint8).reshape(a.height, a.width, a.n)
            y = np.frombuffer(b.samples, np.uint8).reshape(b.height, b.width, b.n)
            allowed = np.zeros((a.height, a.width), dtype=bool)
            for cfg in ref['checkboxes'].values():
                if cfg['page'] != page:
                    continue
                for coords in (cfg['rect'], cfg['previous_border']):
                    if coords:
                        rect = (pymupdf.Rect(coords) + (-1, -1, 1, 1)) * (300/72)
                        allowed[int(rect.y0):int(rect.y1)+1, int(rect.x0):int(rect.x1)+1] = True
            outside = int((np.any(x != y, axis=2) & ~allowed).sum())
            if outside:
                raise ValueError('CHANGES_OUTSIDE_CHECKBOXES')
            checks.append({'page': page, 'dpi': 300, 'outside_changed_pixels': outside})
    output.write_bytes(fixed)
    return {'input_sha256': hashlib.sha256(data).hexdigest(),
            'output_sha256': hashlib.sha256(fixed).hexdigest(), 'checks': checks}
