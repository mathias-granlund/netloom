from __future__ import annotations


def _normalize_flag_name(key: str) -> str:
    return key.replace("-", "_")


def parse_cli(argv: list[str]) -> dict:
    args: dict[str, object] = {}
    positionals: list[str] = []
    completing = "--_complete" in argv

    boolean_flags = {
        "verbose",
        "version",
        "debug",
        "console",
        "all",
        "decrypt",
        "dry_run",
        "continue_on_error",
        "help",
    }

    for item in argv[1:]:
        if item == "--_complete":
            args["_complete"] = True
        elif item.startswith("--_cword="):
            args["_cword"] = int(item.split("=", 1)[1])
        elif item.startswith("--_cur="):
            args["_cur"] = item.split("=", 1)[1]
        elif item in {"?", "-h", "--help"}:
            args["help"] = True
        elif item == "--":
            continue
        elif item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            args[_normalize_flag_name(key)] = value
        elif item.startswith("--"):
            key = _normalize_flag_name(item[2:])
            if key in boolean_flags:
                args[key] = True
            elif completing:
                continue
            else:
                raise ValueError(f"Unknown flag: {item}")
        elif item.startswith("-"):
            if completing:
                continue
            raise ValueError(f"Unknown flag: {item}")
        else:
            positionals.append(item)

    if len(positionals) >= 1:
        args["module"] = positionals[0]
    if positionals[:1] == ["copy"]:
        if len(positionals) >= 2:
            args["copy_module"] = positionals[1]
        if len(positionals) >= 3:
            args["copy_service"] = positionals[2]
        args["legacy_copy_syntax"] = True
    else:
        if len(positionals) >= 2:
            args["service"] = positionals[1]
        if len(positionals) >= 3:
            args["action"] = positionals[2]
            if positionals[2] == "copy":
                args["copy_module"] = positionals[0]
                args["copy_service"] = positionals[1]

    return args
