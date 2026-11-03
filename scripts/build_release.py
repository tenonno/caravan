"""Export only explicitly reviewed files; never export the working Git history."""
import hashlib
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'distribution-files.txt'
FORBIDDEN = {'output', 'presentations', 'dev', '.git', '.agents', '.codex', '.aws',
             '__pycache__', 'node_modules', '.pytest_cache', '.env'}


def release_files(root):
    root = Path(root).resolve()
    names = (root / MANIFEST).read_text(encoding='utf-8').splitlines()
    selected = []
    seen = set()
    for name in names:
        if not name or name.startswith('#'):
            continue
        parts = PurePosixPath(name).parts
        if (not parts or name != PurePosixPath(name).as_posix() or
                name.startswith('/') or ':' in name or '\\' in name or
                any(p in {'.', '..'} or p.lower() in FORBIDDEN or
                    p.lower().startswith('.env.') for p in parts) or
                name.lower() in seen):
            raise ValueError(f'Unsafe or duplicate release path: {name}')
        seen.add(name.lower())
        candidate = root
        for part in parts:
            candidate = candidate / part
            info = candidate.lstat()
            if (stat.S_ISLNK(info.st_mode) or
                    getattr(info, 'st_file_attributes', 0) & 0x400):
                raise ValueError(f'Linked release path: {name}')
        if not candidate.is_file() or not candidate.resolve().is_relative_to(root):
            raise ValueError(f'Not a regular release file: {name}')
        selected.append((name, candidate))
    if not selected:
        raise ValueError('Empty release manifest')
    return sorted(selected)


def build(root, destination):
    files = release_files(root)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.resolve() in {path.resolve() for _, path in files}:
        raise ValueError('Archive must not overwrite a source file')
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in files:
            info = zipfile.ZipInfo('caravan/' + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return hashlib.sha256(destination.read_bytes()).hexdigest(), len(files)


def main():
    destination = ROOT / 'output/distribution/caravan.zip'
    digest, count = build(ROOT, destination)
    (destination.parent / 'SHA256SUMS').write_text(
        f'{digest}  {destination.name}\n', encoding='utf-8')
    print(f'{destination}: {count} files, {destination.stat().st_size:,} bytes')
    print(f'SHA256: {digest}')


if __name__ == '__main__':
    main()
