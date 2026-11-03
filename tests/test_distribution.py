import importlib.util
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_release', ROOT / 'scripts/build_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@contextmanager
def temporary_workspace():
    parent = ROOT / 'output/distribution-tests'
    parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(dir=parent)
    try:
        yield temporary.name
    finally:
        assert Path(temporary.name).resolve().is_relative_to(parent.resolve())
        temporary.cleanup()


class DistributionTests(unittest.TestCase):
    def test_only_allowlisted_files_and_reproducible(self):
        with temporary_workspace() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('public', encoding='utf-8')
            (root / 'private.txt').write_text('must not ship', encoding='utf-8')
            (root / release.MANIFEST).write_text('README.md\n', encoding='utf-8')
            first = root / 'first.zip'
            second = root / 'second.zip'
            self.assertEqual(release.build(root, first), release.build(root, second))
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), ['ai-sindan/README.md'])
                self.assertEqual(archive.read('ai-sindan/README.md'), b'public')

    def test_unsafe_paths_fail_before_creating_archive(self):
        cases = ['../secret', '/secret', 'C:/secret', 'a\\secret', 'a/../secret',
                 'output/report.json', '.git/config', 'presentations/notes.txt',
                 'a/.env', 'a/.env.local', 'a/__pycache__/x.pyc', 'a//b',
                 'README.md\nreadme.md']
        with temporary_workspace() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('public', encoding='utf-8')
            for name in cases:
                with self.subTest(name=name):
                    (root / release.MANIFEST).write_text(name, encoding='utf-8')
                    with self.assertRaises(ValueError):
                        release.build(root, root / 'release.zip')
                    self.assertFalse((root / 'release.zip').exists())

    def test_missing_listed_file_fails(self):
        with temporary_workspace() as directory:
            root = Path(directory)
            (root / release.MANIFEST).write_text('missing.py', encoding='utf-8')
            with self.assertRaises(FileNotFoundError):
                release.build(root, root / 'release.zip')
            self.assertFalse((root / 'release.zip').exists())

    def test_complete_skill_and_extracted_notice(self):
        selected = {name for name, _ in release.release_files(ROOT)}
        skill = ROOT / 'skills/ai-sindan'
        expected = {p.relative_to(ROOT).as_posix() for p in skill.rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        self.assertTrue(expected <= selected, expected - selected)
        self.assertTrue({'LICENSE', 'README.md', release.MANIFEST} <= selected)
        with temporary_workspace() as directory:
            archive_path = Path(directory) / 'release.zip'
            release.build(ROOT, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(Path(directory) / 'unpacked')
            unpacked = Path(directory) / 'unpacked/ai-sindan'
            result = subprocess.run(
                [sys.executable, 'skills/ai-sindan/scripts/semantic.py', 'notice'],
                cwd=unpacked, capture_output=True, encoding='utf-8',
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.strip())
            self.assertFalse((unpacked / 'output').exists())


if __name__ == '__main__':
    unittest.main()
