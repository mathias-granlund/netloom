import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version
from pathlib import Path


def _source_version() -> str | None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    try:
        text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def get_version() -> str:
    source_version = _source_version()
    for package_name in ("netloom-tool",):
        try:
            installed_version = _version(package_name)
            if source_version and installed_version != source_version:
                continue
            return installed_version
        except PackageNotFoundError:
            continue
    return source_version or "1.10.2"
