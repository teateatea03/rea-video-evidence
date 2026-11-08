"""A public installer must not overwrite user-owned skills."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_skill.py"


def run(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_install_to_unicode_destination(tmp_path):
    destination = tmp_path / "中文 技能" / "rea-video"
    result = run("--dest", destination)
    assert result.returncode == 0, result.stderr
    source = ROOT / "skills" / "rea-video"
    for path in source.rglob("*.md"):
        assert (destination / path.relative_to(source)).read_bytes() == path.read_bytes()


def test_existing_skill_is_not_overwritten(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "SKILL.md"
    sentinel.write_bytes(b"user-owned skill")
    result = run("--dest", destination)
    assert result.returncode == 2
    assert sentinel.read_bytes() == b"user-owned skill"
    assert list(destination.iterdir()) == [sentinel]


def test_codex_home_is_honored(tmp_path):
    env = {**os.environ, "CODEX_HOME": str(tmp_path / "codex-home"), "PYTHONUTF8": "1"}
    result = run("--agent", "codex", env=env)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "codex-home/skills/rea-video/SKILL.md").is_file()


def test_destination_inside_source_is_rejected():
    destination = ROOT / "skills/rea-video/recursive-copy"
    assert not destination.exists()
    result = run("--dest", destination)
    assert result.returncode == 2 and not destination.exists()
