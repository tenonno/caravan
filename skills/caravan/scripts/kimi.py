"""Read the verified Windows Kimi desktop Wire 1.5 format, without running Kimi."""
from datetime import datetime, timezone
import json

DESKTOP_HOME = 'AppData/Roaming/kimi-desktop/daimon-share/daimon/runtime/kimi-code/home'


def sessions(home, stats, excluded):
    root = home / DESKTOP_HOME
    index = root / 'session_index.jsonl'
    if not index.is_file():
        return
    projects = {}
    try:
        for line in index.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
                sid, project = row['sessionId'], row['workDir']
                if not isinstance(sid, str) or not isinstance(project, str) or not project:
                    raise ValueError()
                projects[sid] = project
            except (ValueError, KeyError, TypeError):
                stats['kimi_invalid_index_rows'] += 1
    except (OSError, UnicodeError):
        stats['kimi_unreadable_index'] += 1
        return
    # Never follow sessionDir from an index into an arbitrary directory. Read only
    # desktop conversation sessions: ctitle-* is automatic title generation.
    for path in sorted((root / 'sessions').glob('*/*/agents/main/wire.jsonl')):
        sid = path.parents[2].name
        if not sid.startswith('conv-'):
            stats['kimi_excluded_auxiliary_sessions'] += 1
            continue
        if 'kimi:' + sid in excluded:
            stats['excluded_sessions'] += 1
            continue
        if sid not in projects:
            stats['kimi_missing_project'] += 1
            continue
        yield path, dict(id=sid, project=projects[sid])


def rows(path, stats):
    """Emit canonical messages only; duplicate context/stream records are ignored."""
    seen = set()
    with path.open(encoding='utf-8') as stream:
        try:
            header = json.loads(next(stream))
            if not isinstance(header, dict) or header.get('type') != 'metadata' or header.get('protocol_version') != '1.5':
                raise ValueError()
        except (StopIteration, ValueError):
            stats['kimi_unsupported_wire_format'] += 1
            return
        for line in stream:
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError()
            except ValueError:
                stats['malformed_lines'] += 1
                continue
            if row.get('type') != 'agent.message.appended' or row.get('kind') != 'event':
                continue
            if row.get('agentId', 'main') != 'main':
                continue
            envelope = row.get('message')
            if not isinstance(envelope, dict):
                continue
            message, meta = envelope.get('message'), envelope.get('meta')
            if not isinstance(message, dict) or not isinstance(meta, dict):
                continue
            role = message.get('role')
            origin = meta.get('origin')
            finish = meta.get('finish')
            if role == 'user':
                if meta.get('source') != 'input' or not isinstance(origin, dict) or origin.get('kind') != 'user':
                    continue
                key = meta.get('userMessageId')
            elif role == 'assistant':
                if (meta.get('source') != 'llm' or not isinstance(finish, dict)
                        or finish.get('finishReason') != 'completed' or message.get('toolCalls')):
                    continue
                key = meta.get('messageId')
            else:
                continue
            stamp = row.get('time')
            if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
                stats['kimi_invalid_timestamp'] += 1
                continue
            try:
                stamp = datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()
            except (ValueError, OverflowError, OSError):
                stats['kimi_invalid_timestamp'] += 1
                continue
            content = message.get('content')
            if not isinstance(content, list):
                continue
            text = '\n'.join(b['text'] for b in content if isinstance(b, dict)
                             and b.get('type') == 'text' and isinstance(b.get('text'), str))
            if not text:
                continue
            # Stable IDs suppress replayed rows even if their replay time differs.
            identity = (role, key) if isinstance(key, str) and key else (role, stamp, text)
            if identity in seen:
                continue
            seen.add(identity)
            yield dict(type=role, timestamp=stamp, message=dict(content=text))
