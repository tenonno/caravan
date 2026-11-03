"""Caravan's display identity; never part of a saved diagnosis or share profile."""
import base64
from pathlib import Path


def embed_logo(template):
    if '__BRANDLOGO__' not in template:
        return template
    logo = Path(__file__).resolve().parent.parent / 'assets/brand/caravan-logo.png'
    uri = 'data:image/png;base64,' + base64.b64encode(logo.read_bytes()).decode('ascii')
    return template.replace('__BRANDLOGO__', uri)
