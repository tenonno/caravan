"""Read Antigravity CLI transcripts; never launch the CLI or decode private blobs."""
import json
import re
import sqlite3
from urllib.parse import quote, unquote, urlsplit


def workspace_path(uri):
    parsed = urlsplit(uri)
    if parsed.scheme != 'file':
        return uri
    path = unquote(parsed.path)
    if parsed.netloc:
        return '//' + parsed.netloc + path
    return path[1:] if re.match(r'^/[A-Za-z]:/', path) else path


def summaries(root, stats):
    """Only read routing metadata, not titles, previews or serialized payloads."""
    path = root / 'conversation_summaries.db'
    if not path.exists():
        return {}
    connection = None
    try:
        # immutable avoids journal creation on read-only Windows directories.
        # Never use it when a WAL exists: that could hide recent metadata.
        wal = path.with_name(path.name + '-wal')
        mode = '?mode=ro' if wal.exists() else '?mode=ro&immutable=1'
        connection = sqlite3.connect('file:' + quote(path.resolve().as_posix(), safe='/:') + mode, uri=True)
        result = {}
        for sid, uris, parent in connection.execute(
                'SELECT conversation_id, workspace_uris, parent_conversation_id FROM conversation_summaries'):
            try:
                paths = json.loads(uris or '[]')
                if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                    raise ValueError('Invalid workspace list')
                project = workspace_path(paths[0]) if paths else None
            except (ValueError, TypeError):
                stats['antigravity_invalid_workspace'] += 1
                project = None
            result[sid] = dict(project=project, parent=parent)
        return result
    except (sqlite3.Error, OSError):
        stats['antigravity_unreadable_metadata'] += 1
        return {}
    finally:
        if connection is not None:
            connection.close()


def sessions(home, stats, excluded):
    root = home / '.gemini/antigravity-cli'
    metadata = summaries(root, stats)
    # Exact path only: transcript_full and chunks repeat the same conversation.
    for path in sorted((root / 'brain').glob('*/.system_generated/logs/transcript.jsonl')):
        sid = path.parents[2].name
        if 'antigravity:' + sid in excluded:
            stats['excluded_sessions'] += 1
            continue
        info = metadata.get(sid, {})
        if info.get('parent'):
            stats['excluded_subagent_files'] += 1
            continue
        if not info.get('project'):
            stats['antigravity_missing_project'] += 1
        yield path, dict(id=sid, project=info.get('project') or 'antigravity:unknown-project')


def message(row, stats):
    if row.get('status') != 'DONE':
        return None
    kind, source, content = row.get('type'), row.get('source'), row.get('content')
    if not isinstance(content, str):
        return None
    if kind == 'USER_INPUT' and source == 'USER_EXPLICIT':
        # Only the request is authored by the user. Metadata/settings may follow.
        match = re.fullmatch(r'\s*<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>.*', content, re.S)
        if not match:
            stats['antigravity_unsupported_user_format'] += 1
            return None
        return row.get('created_at'), 'user', match.group(1)
    if kind == 'PLANNER_RESPONSE' and source == 'MODEL':
        return row.get('created_at'), 'assistant', content
    return None
