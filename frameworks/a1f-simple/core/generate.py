#!/usr/bin/env python3
"""Clean API wrapper for a1f-simple framework."""
from pathlib import Path
from typing import Any, Dict

from . import a1_core

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = FRAMEWORK_ROOT / "templates" / "a1_template_v1.pdf"
LAYOUT = FRAMEWORK_ROOT / "config" / "a1_layout.json"


def generate(form: Dict[str, Any], output_pdf: str | Path, **kwargs) -> Path:
    """Generate PDF by replacing placeholders. Checkbox handling allowed.
    
    Args:
        form: Worker data with values for all placeholders
        output_pdf: Output file path
        layout_json: Optional path to layout for checkbox positions
        erase_empty: Whether to erase empty placeholders
        
    Returns:
        Path to generated PDF
    """
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE}")
    
    layout_path = None
    if 'layout_json' in kwargs and kwargs['layout_json'] is not None:
        layout_path = kwargs['layout_json']
    elif LAYOUT.exists():
        layout_path = LAYOUT
    
    return a1_core.generate_a1_pdf(
        form=form,
        output_pdf=output_pdf,
        layout_json=layout_path,
        erase_empty=kwargs.get('erase_empty', False),
    )
