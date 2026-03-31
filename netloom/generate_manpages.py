from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManpageSpec:
    stem: str
    title: str
    section: str
    manual: str

    @property
    def markdown_path(self) -> Path:
        return _project_root() / "man" / f"{self.stem}.md"

    @property
    def roff_path(self) -> Path:
        suffix = f".{self.section}"
        return _project_root() / "netloom" / "data" / "man" / f"{self.stem}{suffix}"


MANPAGE_SPECS = (
    ManpageSpec(
        stem="netloom",
        title="NETLOOM",
        section="1",
        manual="User Commands",
    ),
    ManpageSpec(
        stem="netloom-clearpass",
        title="NETLOOM-CLEARPASS",
        section="7",
        manual="Miscellaneous Information Manual",
    ),
)

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_NAME_SECTION_RE = re.compile(
    r"^(?P<name>[\w-]+)\s+is\s+(?:the\s+)?(?P<desc>.+?)(?:\.)?$", re.IGNORECASE
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_version() -> str:
    pyproject = (_project_root() / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not match:
        raise ValueError("Could not find project version in pyproject.toml")
    return match.group(1)


def _release_label(version: str) -> str:
    changelog = (_project_root() / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"^##\s+{re.escape(version)}\s+-\s+(\d{{4}})-(\d{{2}})-(\d{{2}})$",
        changelog,
        re.MULTILINE,
    )
    if not match:
        raise ValueError(f"Could not find release date for {version} in CHANGELOG.md")
    year, month, _day = match.groups()
    month_names = {
        "01": "January",
        "02": "February",
        "03": "March",
        "04": "April",
        "05": "May",
        "06": "June",
        "07": "July",
        "08": "August",
        "09": "September",
        "10": "October",
        "11": "November",
        "12": "December",
    }
    return f'{month_names[month]} {year}'


def _strip_source_preamble(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines):
        if line.startswith("## "):
            return lines[index:]
    return []


def _plain_text(text: str) -> str:
    text = _LINK_RE.sub(lambda match: match.group(1), text)
    text = _INLINE_CODE_RE.sub(lambda match: match.group(1), text)
    text = text.replace("**", "").replace("*", "")
    return " ".join(text.strip().split())


def _roff_text(text: str) -> str:
    return _plain_text(text).replace("\\", "\\\\")


def _is_list_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("- ") or bool(re.match(r"\d+\.\s+", stripped))


def _is_paragraph_start(line: str) -> bool:
    return bool(line.strip()) and not (
        line.startswith("## ")
        or line.startswith("### ")
        or line.startswith("```")
        or _is_list_line(line)
    )


def _render_name_line(text: str) -> str:
    match = _NAME_SECTION_RE.match(_plain_text(text))
    if not match:
        return _roff_text(text)
    return f'{match.group("name")} \\- {match.group("desc")}'


def render_roff(spec: ManpageSpec, markdown: str, *, version: str, release: str) -> str:
    lines = _strip_source_preamble(markdown.splitlines())
    header = (
        f'.TH {spec.title} {spec.section} "{release}" '
        f'"netloom {version}" "{spec.manual}"'
    )
    output = [header]

    current_section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if line.startswith("## "):
            current_section = line[3:].strip().upper()
            output.append(f".SH {current_section}")
            i += 1
            continue

        if line.startswith("### "):
            output.append(f'.SS "{_roff_text(line[4:])}"')
            i += 1
            continue

        if line.startswith("```"):
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            output.extend([".PP", ".EX", *code_lines, ".EE"])
            i += 1
            continue

        if stripped.startswith("- "):
            while i < len(lines):
                item_line = lines[i].strip()
                if not item_line.startswith("- "):
                    break
                item = item_line[2:]
                i += 1
                while i < len(lines):
                    cont = lines[i]
                    cont_stripped = cont.strip()
                    if (
                        not cont_stripped
                        or cont.startswith("## ")
                        or cont.startswith("### ")
                        or cont.startswith("```")
                        or _is_list_line(cont)
                    ):
                        break
                    item += " " + cont_stripped
                    i += 1
                output.extend(['.IP "\\[bu]" 2', _roff_text(item)])
                while i < len(lines) and not lines[i].strip():
                    i += 1
            continue

        if re.match(r"\d+\.\s+", stripped):
            while i < len(lines):
                item_line = lines[i].strip()
                match = re.match(r"(\d+)\.\s+(.*)", item_line)
                if not match:
                    break
                number, item = match.groups()
                i += 1
                while i < len(lines):
                    cont = lines[i]
                    cont_stripped = cont.strip()
                    if (
                        not cont_stripped
                        or cont.startswith("## ")
                        or cont.startswith("### ")
                        or cont.startswith("```")
                        or _is_list_line(cont)
                    ):
                        break
                    item += " " + cont_stripped
                    i += 1
                output.extend([f'.IP "{number}." 4', _roff_text(item)])
                while i < len(lines) and not lines[i].strip():
                    i += 1
            continue

        if _is_paragraph_start(line):
            paragraph_parts = [stripped]
            i += 1
            while i < len(lines) and _is_paragraph_start(lines[i]):
                paragraph_parts.append(lines[i].strip())
                i += 1
            text = " ".join(paragraph_parts)
            output.append(".PP")
            if current_section == "NAME":
                output.append(_render_name_line(text))
            else:
                output.append(_roff_text(text))
            continue

        i += 1

    return "\n".join(output).rstrip() + "\n"


def rendered_manpages(
    *, version: str | None = None, release: str | None = None
) -> dict[Path, str]:
    active_version = version or _read_version()
    active_release = release or _release_label(active_version)
    rendered: dict[Path, str] = {}
    for spec in MANPAGE_SPECS:
        markdown = spec.markdown_path.read_text(encoding="utf-8")
        rendered[spec.roff_path] = render_roff(
            spec, markdown, version=active_version, release=active_release
        )
    return rendered


def write_manpages() -> list[Path]:
    written: list[Path] = []
    for path, text in rendered_manpages().items():
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def check_manpages() -> list[Path]:
    out_of_date: list[Path] = []
    for path, expected in rendered_manpages().items():
        current = path.read_text(encoding="utf-8")
        if current.replace("\r\n", "\n") != expected:
            out_of_date.append(path)
    return out_of_date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netloom-generate-manpages",
        description=(
            "Generate installable roff man pages under netloom/data/man from the "
            "markdown sources in man/."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if any generated man page is out of date.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.check:
        stale = check_manpages()
        if stale:
            raise SystemExit(
                "Generated man pages are out of date:\n"
                + "\n".join(f"  {path}" for path in stale)
            )
        print("Man pages are up to date.")
        return

    written = write_manpages()
    print("Generated man pages:")
    for path in written:
        print(f"  {path}")


__all__ = [
    "MANPAGE_SPECS",
    "ManpageSpec",
    "build_parser",
    "check_manpages",
    "main",
    "render_roff",
    "rendered_manpages",
    "write_manpages",
]
