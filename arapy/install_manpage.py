from __future__ import annotations

import argparse
import shutil
from importlib.resources import as_file, files
from pathlib import Path


def default_man1_dir() -> Path:
    return Path.home() / ".local" / "share" / "man" / "man1"


def resolve_target_dir(raw: str | None) -> Path:
    if not raw:
        return default_man1_dir()
    path = Path(raw).expanduser()
    return path if path.name == "man1" else path / "man1"


def bundled_manpage():
    return files("arapy").joinpath("data", "man", "arapy.1")


def install_manpage(target_dir: str | Path | None = None) -> Path:
    destination_dir = resolve_target_dir(str(target_dir) if target_dir else None)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / "arapy.1"
    with as_file(bundled_manpage()) as source:
        shutil.copyfile(source, destination)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arapy-install-manpage",
        description="Install the bundled arapy(1) man page into a local man directory.",
    )
    parser.add_argument(
        "--dir",
        dest="target_dir",
        help="Target man directory or man base directory. Defaults to ~/.local/share/man/man1",
    )
    parser.add_argument(
        "--print-path",
        action="store_true",
        help="Print only the installed man page path.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    installed_path = install_manpage(args.target_dir)

    if args.print_path:
        print(installed_path)
        return

    print(f"Installed man page to {installed_path}")
    print(f"View with: man -l {installed_path}")
    if installed_path.parent == default_man1_dir():
        print("If `man arapy` still does not work, add ~/.local/share/man to MANPATH.")
