"""Semantic observation definitions. Categories describe choices, never merit."""
import json
from pathlib import Path
import diagnose as base

PROCESS = json.loads((Path(__file__).parent.parent/'assets/process-perspectives.json').read_text(encoding='utf-8'))
TOOLING = json.loads((Path(__file__).parent.parent/'assets/tooling-perspectives.json').read_text(encoding='utf-8'))
PERSPECTIVES = base.PERSPECTIVES + PROCESS + TOOLING
PROCESS_BY_ID = {p['id']: p for p in PROCESS}
TOOLING_IDS = {p['id'] for p in TOOLING}
CHOICE_BY_ID = {p['id']: p for p in PROCESS + TOOLING}


def display_report(report):
    """Old results stay old: new dimensions are explicitly not assessed, never zero."""
    present = {p['id'] for p in report['perspectives']}
    missing = [dict(p, not_assessed=True, count=None, sessions=None, assessed_sessions=None,
                    uncertain_sessions=None, not_applicable_sessions=None, session_rate=None,
                    status='未評価', findings=[], observed_forms=[])
               for p in PROCESS + TOOLING if p['id'] not in present]
    return dict(report, perspectives=report['perspectives'] + missing)
