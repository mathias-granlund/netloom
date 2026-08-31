from __future__ import annotations

import argparse
import shutil
from importlib.resources import as_file, files
from pathlib import Path

MANPAGE_FILES = ("netloom.1", "netloom-clearpass.7")


def default_man_dir() -> Path:
    return Path.home() / ".local" / "share" / "man"


def default_man1_dir() -> Path:
    return default_man_dir() / "man1"


def resolve_target_dir(raw: str | None, *, section: str = "man1") -> Path:
    if not raw:
        return default_man_dir() / section
    path = Path(raw).expanduser()
    if path.name == section:
        return path
    if path.name.startswith("man") and path.name[3:].isdigit():
        return path.parent / section
    if path.name == "man":
        return path / section
    return path / section


def bundled_manpage(name: str = "netloom.1"):
    return files("netloom").joinpath("data", "man", name)


def bundled_manpages() -> tuple[str, ...]:
    return MANPAGE_FILES


def manpage_section(name: str) -> str:
    return f"man{name.rsplit('.', 1)[1]}"


def install_manpage(
    target_dir: str | Path | None = None, *, name: str = "netloom.1"
) -> Path:
    destination_dir = resolve_target_dir(
        str(target_dir) if target_dir else None,
        section=manpage_section(name),
    )
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / name
    with as_file(bundled_manpage(name)) as source:
        shutil.copyfile(source, destination)
    return destination


def install_manpages(target_dir: str | Path | None = None) -> list[Path]:
    return [install_manpage(target_dir, name=name) for name in bundled_manpages()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netloom-install-manpage",
        description=(
            "Install the bundled netloom manual pages into a local man directory."
        ),
    )
    parser.add_argument(
        "--dir",
        dest="target_dir",
        help=(
            "Target man directory base or section directory. Defaults to "
            "~/.local/share/man"
        ),
    )
    parser.add_argument(
        "--print-path",
        action="store_true",
        help="Print only the installed man page paths.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    installed_paths = install_manpages(args.target_dir)

    if args.print_path:
        for path in installed_paths:
            print(path)
        return

    print("Installed man pages:")
    for path in installed_paths:
        print(f"  {path}")
    print("View with: man netloom")
    print("Additional plugin guide: man netloom-clearpass")
    if resolve_target_dir(args.target_dir, section="man1") == default_man1_dir():
        print(
            "If `man netloom` or `man netloom-clearpass` still do not work, "
            "add ~/.local/share/man to MANPATH."
        )


if __name__ == "__main__":
    main()
