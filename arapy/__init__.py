from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version


def get_version() -> str:
    try:
        return _version("arapy")
    except PackageNotFoundError:
        return "1.4.2"
