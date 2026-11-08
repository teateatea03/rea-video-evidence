"""Copy this repository's agent skill without replacing an existing installation."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[1] / "skills" / "rea-video"


def default_destination(agent: str) -> Path:
    if agent == "codex":
        return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "rea-video"
    return Path.home() / (".claude" if agent == "claude" else ".agents") / "skills" / "rea-video"


def install(destination: Path) -> Path:
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"destination already exists; nothing overwritten: {destination}")
    if destination.resolve().is_relative_to(SOURCE.resolve()):
        raise ValueError("destination must be outside the source skill directory")
    if not (SOURCE / "SKILL.md").is_file():
        raise FileNotFoundError(f"source skill not found: {SOURCE}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    return destination


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "claude", "agents"), default="codex")
    parser.add_argument("--dest", type=Path, help="exact destination skill directory")
    args = parser.parse_args(argv)
    try:
        destination = install(args.dest if args.dest is not None else default_destination(args.agent))
    except (OSError, ValueError) as exc:
        print(f"install-skill: {exc}", file=sys.stderr)
        return 2
    print(f"Installed skill: {destination}")
    print("CLI installation is separate. Your agent may need to refresh/reload its skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
