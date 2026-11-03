"""Private, dependency-free coding-agent interaction report. Python 3.10+."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import brand

VERSION = '0.4.0'
TYPES = json.loads((Path(__file__).parent.parent / 'assets/types.json').read_text(encoding='utf-8'))
PERSPECTIVES = json.loads((Path(__file__).parent.parent / 'assets/perspectives.json').read_text(encoding='utf-8'))
CLASSIFICATION_RULES = dict(evidence_smoothing=3, repeated_messages=3, repeated_sessions=2,
                            min_messages=20, min_sessions=3, min_repeated_dimensions=3,
                            min_supported_dimensions=2, min_similarity=.45, candidate_gap=.06,
                            score_decimals=4)

def score_styles(perspectives, sessions, catalog=None):
    # Each conversation has equal influence. Shrink rare matches; no negative trait is inferred.
    rules = CLASSIFICATION_RULES
    classification_ids = {p['id'] for p in PERSPECTIVES}
    perspectives = [p for p in perspectives if p['id'] in classification_ids]
    vector = {p['id']: (p['sessions'] / p.get('assessed_sessions',sessions)) * p['count'] / (p['count'] + rules['evidence_smoothing'])
              for p in perspectives if p['count'] and p.get('assessed_sessions',sessions)}
    norm = math.sqrt(sum(v*v for v in vector.values()))
    repeated = {p['id'] for p in perspectives if p['sessions'] >= rules['repeated_sessions'] and p['count'] >= rules['repeated_messages']}
    ranked = []
    for t in TYPES if catalog is None else catalog:
        weights = t['weights']
        denom = norm * math.sqrt(sum(v*v for v in weights.values()))
        score = sum(vector.get(k, 0)*v for k,v in weights.items()) / denom if denom else 0
        reasons = sorted((p for p in perspectives if p['id'] in weights and p['id'] in repeated),
                         key=lambda p: -vector[p['id']] * weights[p['id']])
        ranked.append(dict(code=t['code'], name=t['name'], score=round(score, rules['score_decimals']),
                           reasons=[p['id'] for p in reasons], supported=len(reasons)))
    ranked.sort(key=lambda t: (-t['score'], t['code']))
    return vector, repeated, ranked


def classify(perspectives, messages, sessions):
    rules = CLASSIFICATION_RULES
    vector, repeated, ranked = score_styles(perspectives, sessions)
    adequate = messages >= rules['min_messages'] and sessions >= rules['min_sessions'] and len(repeated) >= rules['min_repeated_dimensions']
    eligible = [t for t in ranked if t['supported'] >= rules['min_supported_dimensions'] and t['score'] >= rules['min_similarity']] if adequate else []
    candidates = [t for t in eligible if eligible[0]['score']-t['score'] < rules['candidate_gap']]
    primary = next((t for t in TYPES if candidates and t['code']==candidates[0]['code']), None) if len(candidates)==1 else None
    status = '暫定スタイル' if primary else '複数のスタイルが近い' if candidates else '判定材料を集めているところ'
    return dict(type_code=primary['code'] if primary else 'UNDECIDED', type_name=primary['name'] if primary else status,
                profile=primary, type_status=status, candidate_codes=[t['code'] for t in candidates],
                alternatives=eligible[:3], type_catalog=TYPES, repeated_dimensions=len(repeated),
                evidence_ready=adequate)


def make_share(report):
    # Explicit allowlist: no timestamps, paths, source tools, source text, exact sample sizes, or arbitrary labels.
    style=report.get('portrait',{}).get('classification',report)
    method=report['method']+('+'+report['portrait']['schema'] if 'portrait' in report else '')
    return dict(schema='ai-sindan-share-v1', method=method, days=report['days'],
                sample='比較の材料あり' if style['evidence_ready'] else '材料が少ない',
                type_name=style['type_name'], candidate_codes=style['candidate_codes'],
                metrics=[dict(id=p['id'], session_rate=p['session_rate'], status=p['status'],
                              **({'forms':[f['id'] for f in p.get('observed_forms',[]) if f['sessions']]} if p.get('kind') in ('process','tooling') else {}))
                         for p in report['perspectives'] if not p.get('not_assessed')])


def parse_time(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except (ValueError, TypeError):
        return None

def clean_text(text):
    # Remove environment/agent wrappers, quoted excerpts, and pasted code.
    if re.match(r'\s*(# AGENTS\.md instructions|The following is the Codex agent history|This block is automatically supplied ambient UI state)', text):
        return ''
    text = re.sub(r'<(in-app-browser-context|environment_context|external_codex_apps[^\s>]*|guardian_tool_descriptions|system-reminder|node_repl_review_evidence|turn_aborted|image)\b[^>]*>.*?</\1>', '', text, flags=re.S)
    if re.match(r'\s*<(environment_context|external_codex_apps|guardian_tool|no retained|node_repl|turn_aborted)', text):
        return ''
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'<[^>]+>', '', text)
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('>')).strip()

def content_text(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ''
    return '\n'.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') in ('text', 'input_text', 'output_text'))

def read_session(path, source, stats):
    """Canonical user messages only; event_msg is a fallback, never counted twice."""
    primary, fallback = [], []
    session_id = path.stem
    try:
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        raise ValueError('not an object')
                except (ValueError, UnicodeError):
                    stats['malformed_lines'] += 1
                    continue
                p = obj.get('payload') or {}
                if not isinstance(p, dict):
                    continue
                if obj.get('type') == 'session_meta':
                    origin = p.get('source')
                    if isinstance(origin, dict) and 'subagent' in origin:
                        stats['excluded_subagent_files'] += 1
                        return session_id, []
                    session_id = p.get('id', session_id)
                if source == 'codex':
                    if obj.get('type') == 'response_item' and p.get('role') == 'user' and p.get('type') == 'message':
                        primary.append((obj.get('timestamp'), content_text(p.get('content')), None))
                    elif obj.get('type') == 'event_msg' and p.get('type') == 'user_message':
                        fallback.append((obj.get('timestamp'), p.get('message', ''), None))
                elif obj.get('type') == 'user' and not obj.get('isSidechain') and not obj.get('isMeta'):
                    msg = obj.get('message') or {}
                    if isinstance(msg, dict):
                        primary.append((obj.get('timestamp'), content_text(msg.get('content')), obj.get('uuid')))
                        session_id = obj.get('sessionId', session_id)
    except (OSError, UnicodeError):
        stats['unreadable_files'] += 1
    return session_id, primary or fallback

def analyze(home, days=90, source='all', now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    roots = [('codex', home / '.codex/sessions'), ('codex', home / '.codex/archived_sessions'), ('claude', home / '.claude/projects')]
    stats = Counter(); sources = Counter(); sessions = set(); seen = set(); dates = []
    perspective_patterns = [re.compile(p['pattern'], re.I) for p in PERSPECTIVES]
    perspective_hits = [0] * len(PERSPECTIVES)
    perspective_sessions = [set() for _ in PERSPECTIVES]
    for kind, root in roots:
        if source != 'all' and kind != source:
            continue
        for path in sorted(root.rglob('*.jsonl')):
            if 'subagents' in path.parts:
                continue
            stats['files_scanned'] += 1
            sid, messages = read_session(path, kind, stats)
            for timestamp, raw, uid in messages:
                date = parse_time(timestamp)
                if date is None:
                    stats['missing_timestamp'] += 1
                    continue
                if not cutoff <= date <= now:
                    continue
                text = clean_text(raw)
                if not text:
                    continue
                key = (kind, sid, uid or (timestamp, text))
                if key in seen:
                    continue
                seen.add(key); sessions.add((kind, sid)); dates.append(date)
                sources[kind] += 1
                for i, pattern in enumerate(perspective_patterns):
                    if pattern.search(text):
                        perspective_hits[i] += 1
                        perspective_sessions[i].add((kind, sid))
    total_messages = sum(sources.values())
    perspectives = []
    for i, p in enumerate(PERSPECTIVES):
        count = perspective_hits[i]
        session_count = len(perspective_sessions[i])
        perspectives.append(dict(
            **{k: v for k, v in p.items() if k != 'pattern'},
            count=count, sessions=session_count,
            rate=round(100 * count / total_messages, 1) if total_messages else None,
            session_rate=round(100 * session_count / len(sessions), 1) if sessions else None,
            status='複数の会話で観測' if count >= 5 and session_count >= 2 else '少数の表現を観測' if count else '未観測',
        ))
    classification = classify(perspectives, total_messages, len(sessions))
    return dict(version=VERSION, generated_at=now.isoformat(), days=days, source_filter=source,
                period=[min(dates).isoformat(), max(dates).isoformat()] if dates else None,
                messages=sum(sources.values()), sessions=len(sessions), sources=dict(sources),
                diagnostics=dict(stats), perspectives=perspectives, **classification,
                provisional=True, method='habits-18-prototypes-v1')

def render(report):
    name = 'semantic-report.html' if report['method'].startswith('semantic-') else 'report.html'
    template = brand.embed_logo((Path(__file__).parent.parent / 'assets' / name).read_text(encoding='utf-8'))
    # No raw logs enter this HTML. Escaping also protects future schema extensions.
    import journey
    view = dict(report, rendered_at=datetime.now(timezone.utc).isoformat())
    if name == 'semantic-report.html':
        import backup, rubric
        if 'private_backup' not in view: view['private_backup'] = dict(schema=backup.SCHEMA,report=report,execution_audit=None)
        view['viewer_assets'] = journey.presentation({'portrait':{'schema':'portrait-v1'}})
        view['viewer_definitions'] = [{k:v for k,v in p.items() if k!='pattern'} for p in rubric.PERSPECTIVES]
        template = template.replace('__PRIVATE_BACKUP_JS__', (Path(__file__).parent.parent/'assets/private-backup.js').read_text(encoding='utf-8'))
    artwork = journey.presentation(report)
    if artwork is not None:
        view['journey'] = artwork
    payload = json.dumps(view, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return template.replace('__REPORT_DATA__', payload)

def main():
    parser = argparse.ArgumentParser(description='ローカルのAI対話履歴から診断HTMLを生成（通信なし）')
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--output', type=Path, default=Path('output'))
    parser.add_argument('--days', type=int, default=90)
    parser.add_argument('--source', choices=['all', 'codex', 'claude'], default='all')
    args = parser.parse_args()
    if args.days < 1:
        parser.error('--days must be positive')
    report = analyze(args.home, args.days, args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    target = args.output / 'index.html'
    markup = render(report)
    target.write_text(markup, encoding='utf-8')
    (args.output / 'share-profile.json').write_text(json.dumps(make_share(report), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Report: {target.resolve()}')
    print(f"Messages: {report['messages']} / Sessions: {report['sessions']} / Type: {report['type_code']}")
    print('Diagnostics: ' + json.dumps(report['diagnostics']))

if __name__ == '__main__':
    main()
