from __future__ import annotations

import argparse
from typing import Any

BUILTIN_MODULES = {"cache", "load", "server"}
BOOLEAN_FLAGS = {
    "verbose",
    "version",
    "debug",
    "console",
    "all",
    "show_all",
    "decrypt",
    "dry_run",
    "continue_on_error",
    "help",
}
GLOBAL_VALUE_FLAGS = {
    "api_token",
    "api_token_file",
    "token",
    "token_file",
    "catalog_view",
    "log_level",
    "out",
    "data_format",
    "csv_fieldnames",
    "file",
    "filter",
    "limit",
    "offset",
    "sort",
    "calculate_count",
    "encrypt",
}


class CliParseError(ValueError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliParseError(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if status == 0:
            raise CliParseError(message or "")
        raise CliParseError(message or f"exited with status {status}")


def _normalize_flag_name(key: str) -> str:
    return key.replace("-", "_")


def _flag_names(name: str) -> list[str]:
    dashed = name.replace("_", "-")
    if dashed == name:
        return [f"--{name}"]
    return [f"--{dashed}", f"--{name}"]


def _update_args(target: dict[str, Any], values: dict[str, Any]) -> None:
    for key, value in values.items():
        if value is None:
            continue
        if value is False:
            continue
        target[key] = value


def _namespace_dict(namespace: argparse.Namespace) -> dict[str, Any]:
    return vars(namespace)


def _add_shared_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-h", "--help", dest="help", action="store_true")
    parser.add_argument("--version", dest="version", action="store_true")
    parser.add_argument(*_flag_names("verbose"), dest="verbose", action="store_true")
    parser.add_argument(*_flag_names("debug"), dest="debug", action="store_true")
    parser.add_argument(*_flag_names("console"), dest="console", action="store_true")
    parser.add_argument(*_flag_names("decrypt"), dest="decrypt", action="store_true")
    parser.add_argument(
        *_flag_names("catalog_view"),
        dest="catalog_view",
        choices=("visible", "full"),
    )
    parser.add_argument(*_flag_names("log_level"), dest="log_level")
    parser.add_argument(*_flag_names("api_token"), dest="api_token")
    parser.add_argument(*_flag_names("token"), dest="token")
    parser.add_argument(*_flag_names("token_file"), dest="token_file")
    parser.add_argument(*_flag_names("api_token_file"), dest="api_token_file")
    parser.add_argument(*_flag_names("out"), dest="out")
    parser.add_argument(*_flag_names("data_format"), dest="data_format")
    parser.add_argument(*_flag_names("csv_fieldnames"), dest="csv_fieldnames")
    parser.add_argument(*_flag_names("file"), dest="file")
    parser.add_argument(*_flag_names("filter"), dest="filter")
    parser.add_argument(*_flag_names("limit"), dest="limit")
    parser.add_argument(*_flag_names("offset"), dest="offset")
    parser.add_argument(*_flag_names("sort"), dest="sort")
    parser.add_argument(*_flag_names("calculate_count"), dest="calculate_count")
    parser.add_argument(*_flag_names("encrypt"), dest="encrypt")


def _build_global_parser() -> _ArgumentParser:
    parser = _ArgumentParser(add_help=False, allow_abbrev=False)
    _add_shared_options(parser)
    return parser


def _build_builtin_parser() -> _ArgumentParser:
    parser = _ArgumentParser(add_help=False, allow_abbrev=False)
    _add_shared_options(parser)
    subparsers = parser.add_subparsers(dest="module")

    load_parser = subparsers.add_parser("load", add_help=False, allow_abbrev=False)
    load_parser.add_argument("service", nargs="?")

    server_parser = subparsers.add_parser("server", add_help=False, allow_abbrev=False)
    server_parser.add_argument("service", nargs="?")
    server_parser.add_argument("action", nargs="?")

    cache_parser = subparsers.add_parser("cache", add_help=False, allow_abbrev=False)
    cache_parser.add_argument("service", nargs="?")

    return parser


def _extract_completion_tokens(tokens: list[str]) -> tuple[dict[str, Any], list[str]]:
    args: dict[str, Any] = {}
    remaining: list[str] = []

    for item in tokens:
        if item == "--_complete":
            args["_complete"] = True
        elif item.startswith("--_cword="):
            args["_cword"] = int(item.split("=", 1)[1])
        elif item.startswith("--_cur="):
            args["_cur"] = item.split("=", 1)[1]
        else:
            remaining.append(item)

    return args, remaining


def _strip_bare_question_help(tokens: list[str]) -> tuple[bool, list[str]]:
    help_requested = False
    remaining: list[str] = []

    for item in tokens:
        if item == "?":
            help_requested = True
            continue
        remaining.append(item)

    return help_requested, remaining


def _completion_parse(tokens: list[str], initial: dict[str, Any]) -> dict[str, Any]:
    args = dict(initial)
    positionals: list[str] = []

    for item in tokens:
        if item == "--":
            continue
        if item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            args[_normalize_flag_name(key)] = value
            continue
        if item.startswith("-"):
            continue
        positionals.append(item)

    if len(positionals) >= 1:
        args["module"] = positionals[0]
    if len(positionals) >= 2:
        args["service"] = positionals[1]
    if len(positionals) >= 3:
        args["action"] = positionals[2]
        if positionals[2] == "copy":
            args["copy_module"] = positionals[0]
            args["copy_service"] = positionals[1]

    return args


def _first_positional(tokens: list[str]) -> str | None:
    for item in tokens:
        if not item.startswith("-"):
            return item
    return None


def _dynamic_context(positionals: list[str]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if len(positionals) >= 1:
        context["module"] = positionals[0]
    if len(positionals) >= 2:
        context["service"] = positionals[1]
    if len(positionals) >= 3:
        context["action"] = positionals[2]
    return context


def _dynamic_parse(tokens: list[str]) -> dict[str, Any]:
    args: dict[str, Any] = {}
    positionals: list[str] = []

    for item in tokens:
        if item == "--":
            continue
        if item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            args[_normalize_flag_name(key)] = value
            continue
        if item in {"-h", "--help"}:
            args["help"] = True
            continue
        if item.startswith("--"):
            key = _normalize_flag_name(item[2:])
            if key in BOOLEAN_FLAGS:
                args[key] = True
                continue
            raise CliParseError(
                f"Unknown flag: {item}",
                context=_dynamic_context(positionals),
            )
        if item.startswith("-"):
            raise CliParseError(
                f"Unknown flag: {item}",
                context=_dynamic_context(positionals),
            )
        positionals.append(item)

    if len(positionals) >= 1:
        args["module"] = positionals[0]
    if len(positionals) >= 2:
        args["service"] = positionals[1]
    if len(positionals) >= 3:
        args["action"] = positionals[2]
        if positionals[2] == "copy":
            args["copy_module"] = positionals[0]
            args["copy_service"] = positionals[1]

    return args


def parse_cli(argv: list[str]) -> dict[str, Any]:
    tokens = list(argv[1:])
    completion_args, tokens = _extract_completion_tokens(tokens)
    if completion_args.get("_complete"):
        return _completion_parse(tokens, completion_args)

    bare_help, tokens = _strip_bare_question_help(tokens)

    args: dict[str, Any] = {}
    global_parser = _build_global_parser()
    global_namespace, remaining = global_parser.parse_known_args(tokens)
    _update_args(args, _namespace_dict(global_namespace))

    if bare_help:
        args["help"] = True

    module = _first_positional(remaining)
    if module in BUILTIN_MODULES:
        try:
            builtin_namespace = _build_builtin_parser().parse_args(tokens)
        except CliParseError as exc:
            raise CliParseError(str(exc), context={"module": module}) from exc
        _update_args(args, _namespace_dict(builtin_namespace))
        if bare_help:
            args["help"] = True
        return args

    dynamic_args = _dynamic_parse(remaining)
    _update_args(args, dynamic_args)
    if bare_help:
        args["help"] = True
    return args


__all__ = ["CliParseError", "_normalize_flag_name", "parse_cli"]
