from __future__ import annotations

import os
import shlex
import sys
from dataclasses import dataclass
from os.path import commonprefix
from typing import Any, Callable

from netloom.cli.completion import completion_candidates as cli_completion_candidates
from netloom.cli.parser import CliParseError
from netloom.core.help_shared import (
    display_services_for_module,
    resolve_service_entry,
    service_cli_actions,
)

_GLOBAL_BUILTINS = {"cache", "load", "server", "shell"}
_SHELL_BUILTINS = {"do", "exit", "quit", "show", "top"}


@dataclass(frozen=True)
class ShellContext:
    module: str | None = None
    service: str | None = None


class ShellLineEditor:
    def __init__(
        self,
        shell: "NetloomShell",
        *,
        fallback_input: Callable[[str], str] = input,
    ) -> None:
        self.shell = shell
        self.fallback_input = fallback_input
        self.history: list[str] = []

    def read_line(self, prompt: str) -> str:
        if not self._supports_interactive_editing():
            return self.fallback_input(prompt)
        if os.name == "nt":
            return self._read_line_windows(prompt)
        return self._read_line_posix(prompt)

    def _supports_interactive_editing(self) -> bool:
        return sys.stdin.isatty() and sys.stdout.isatty()

    def _read_line_posix(self, prompt: str) -> str:
        import termios
        import tty

        fd = sys.stdin.fileno()
        original = termios.tcgetattr(fd)
        buffer: list[str] = []
        cursor = 0
        history_index: int | None = None
        history_draft = ""

        try:
            tty.setraw(fd)
            self._render(prompt, buffer, cursor)
            while True:
                raw = os.read(fd, 1)
                if not raw:
                    self._emit("\r\n")
                    raise EOFError
                char = raw.decode("utf-8", errors="ignore")

                if char in {"\r", "\n"}:
                    line = "".join(buffer)
                    self._emit("\r\n")
                    self._remember_history(line)
                    return line

                if char == "\x03":
                    self._emit("^C\r\n")
                    raise KeyboardInterrupt

                if char == "\x04":
                    if not buffer:
                        self._emit("\r\n")
                        raise EOFError
                    if cursor < len(buffer):
                        del buffer[cursor]
                        self._render(prompt, buffer, cursor)
                    continue

                if char in {"\x7f", "\b"}:
                    if cursor > 0:
                        del buffer[cursor - 1]
                        cursor -= 1
                        self._render(prompt, buffer, cursor)
                    else:
                        self._emit("\a")
                    continue

                if char == "\t":
                    buffer, cursor = self._complete_buffer(prompt, buffer, cursor)
                    history_index = None
                    history_draft = ""
                    continue

                if char == "?":
                    self._emit("\r\n")
                    self._emit_block(self.shell.help_text_for_buffer("".join(buffer)))
                    self._emit("\r\n")
                    self._render(prompt, buffer, cursor)
                    continue

                if char == "\x01":
                    cursor = 0
                    self._render(prompt, buffer, cursor)
                    continue

                if char == "\x05":
                    cursor = len(buffer)
                    self._render(prompt, buffer, cursor)
                    continue

                if char == "\x1b":
                    sequence = self._read_escape_sequence_posix(fd)
                    (
                        buffer,
                        cursor,
                        history_index,
                        history_draft,
                    ) = self._handle_escape_sequence(
                        sequence,
                        prompt,
                        buffer,
                        cursor,
                        history_index,
                        history_draft,
                    )
                    continue

                if char.isprintable():
                    buffer.insert(cursor, char)
                    cursor += 1
                    self._render(prompt, buffer, cursor)
                    history_index = None
                    history_draft = ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, original)

    def _read_line_windows(self, prompt: str) -> str:
        import msvcrt

        buffer: list[str] = []
        cursor = 0
        history_index: int | None = None
        history_draft = ""

        self._render(prompt, buffer, cursor)
        while True:
            char = msvcrt.getwch()
            if char in {"\r", "\n"}:
                line = "".join(buffer)
                self._emit("\r\n")
                self._remember_history(line)
                return line

            if char == "\x03":
                self._emit("^C\r\n")
                raise KeyboardInterrupt

            if char == "\x04":
                if not buffer:
                    self._emit("\r\n")
                    raise EOFError
                if cursor < len(buffer):
                    del buffer[cursor]
                    self._render(prompt, buffer, cursor)
                continue

            if char == "\x08":
                if cursor > 0:
                    del buffer[cursor - 1]
                    cursor -= 1
                    self._render(prompt, buffer, cursor)
                else:
                    self._emit("\a")
                continue

            if char == "\t":
                buffer, cursor = self._complete_buffer(prompt, buffer, cursor)
                history_index = None
                history_draft = ""
                continue

            if char == "?":
                self._emit("\r\n")
                self._emit_block(self.shell.help_text_for_buffer("".join(buffer)))
                self._emit("\r\n")
                self._render(prompt, buffer, cursor)
                continue

            if char == "\x00" or char == "\xe0":
                sequence = msvcrt.getwch()
                (
                    buffer,
                    cursor,
                    history_index,
                    history_draft,
                ) = self._handle_escape_sequence(
                    sequence,
                    prompt,
                    buffer,
                    cursor,
                    history_index,
                    history_draft,
                )
                continue

            if char == "\x01":
                cursor = 0
                self._render(prompt, buffer, cursor)
                continue

            if char == "\x05":
                cursor = len(buffer)
                self._render(prompt, buffer, cursor)
                continue

            if char.isprintable():
                buffer.insert(cursor, char)
                cursor += 1
                self._render(prompt, buffer, cursor)
                history_index = None
                history_draft = ""

    def _read_escape_sequence_posix(self, fd: int) -> str:
        raw = os.read(fd, 1)
        if not raw:
            return ""
        sequence = raw.decode("utf-8", errors="ignore")
        if sequence not in {"[", "O"}:
            return sequence
        while True:
            raw = os.read(fd, 1)
            if not raw:
                return sequence
            fragment = raw.decode("utf-8", errors="ignore")
            sequence += fragment
            if fragment.isalpha() or fragment == "~":
                return sequence

    def _handle_escape_sequence(
        self,
        sequence: str,
        prompt: str,
        buffer: list[str],
        cursor: int,
        history_index: int | None,
        history_draft: str,
    ) -> tuple[list[str], int, int | None, str]:
        up_sequences = {"[A", "H"}
        down_sequences = {"[B", "P"}
        right_sequences = {"[C", "M"}
        left_sequences = {"[D", "K"}
        home_sequences = {"[H", "[1~", "OH", "G"}
        end_sequences = {"[F", "[4~", "OF", "O"}
        delete_sequences = {"[3~", "S"}

        if sequence in up_sequences:
            return self._history_up(prompt, buffer, history_index, history_draft)
        if sequence in down_sequences:
            return self._history_down(prompt, buffer, history_index, history_draft)
        if sequence in right_sequences:
            if cursor < len(buffer):
                cursor += 1
                self._render(prompt, buffer, cursor)
            else:
                self._emit("\a")
            return buffer, cursor, history_index, history_draft
        if sequence in left_sequences:
            if cursor > 0:
                cursor -= 1
                self._render(prompt, buffer, cursor)
            else:
                self._emit("\a")
            return buffer, cursor, history_index, history_draft
        if sequence in home_sequences:
            cursor = 0
            self._render(prompt, buffer, cursor)
            return buffer, cursor, history_index, history_draft
        if sequence in end_sequences:
            cursor = len(buffer)
            self._render(prompt, buffer, cursor)
            return buffer, cursor, history_index, history_draft
        if sequence in delete_sequences:
            if cursor < len(buffer):
                del buffer[cursor]
                self._render(prompt, buffer, cursor)
            else:
                self._emit("\a")
            return buffer, cursor, history_index, history_draft
        return buffer, cursor, history_index, history_draft

    def _history_up(
        self,
        prompt: str,
        buffer: list[str],
        history_index: int | None,
        history_draft: str,
    ) -> tuple[list[str], int, int | None, str]:
        if not self.history:
            self._emit("\a")
            return buffer, len(buffer), history_index, history_draft
        if history_index is None:
            history_draft = "".join(buffer)
            history_index = len(self.history) - 1
        elif history_index > 0:
            history_index -= 1
        self._apply_history_line(prompt, buffer, self.history[history_index])
        return buffer, len(buffer), history_index, history_draft

    def _history_down(
        self,
        prompt: str,
        buffer: list[str],
        history_index: int | None,
        history_draft: str,
    ) -> tuple[list[str], int, int | None, str]:
        if history_index is None:
            self._emit("\a")
            return buffer, len(buffer), history_index, history_draft
        if history_index < len(self.history) - 1:
            history_index += 1
            self._apply_history_line(prompt, buffer, self.history[history_index])
            return buffer, len(buffer), history_index, history_draft
        history_index = None
        self._apply_history_line(prompt, buffer, history_draft)
        return buffer, len(buffer), history_index, ""

    def _apply_history_line(self, prompt: str, buffer: list[str], line: str) -> None:
        buffer[:] = list(line)
        self._render(prompt, buffer, len(buffer))

    def _complete_buffer(
        self, prompt: str, buffer: list[str], cursor: int
    ) -> tuple[list[str], int]:
        text = "".join(buffer)
        start, end = _current_token_bounds(text, cursor)
        prefix = text[start:cursor]
        candidates = [
            candidate
            for candidate in self.shell.completion_candidates(text, cursor=cursor)
            if candidate.startswith(prefix)
        ]
        unique_candidates = sorted(set(candidates))
        if not unique_candidates:
            self._emit("\a")
            return buffer, cursor

        if len(unique_candidates) == 1:
            completed = unique_candidates[0]
            replacement = completed if text[end:] else f"{completed} "
            return self._replace_token(prompt, buffer, start, end, replacement)

        shared = commonprefix(unique_candidates)
        if len(shared) > len(prefix):
            return self._replace_token(prompt, buffer, start, end, shared)

        self._emit("\r\n")
        self._emit_block(unique_candidates)
        self._emit("\r\n")
        self._render(prompt, buffer, cursor)
        return buffer, cursor

    def _replace_token(
        self,
        prompt: str,
        buffer: list[str],
        start: int,
        end: int,
        replacement: str,
    ) -> tuple[list[str], int]:
        buffer[start:end] = list(replacement)
        cursor = start + len(replacement)
        self._render(prompt, buffer, cursor)
        return buffer, cursor

    def _render(self, prompt: str, buffer: list[str], cursor: int) -> None:
        text = "".join(buffer)
        self._emit("\r")
        self._emit(prompt)
        self._emit(text)
        self._emit("\x1b[K")
        tail = len(text) - cursor
        if tail > 0:
            self._emit(f"\x1b[{tail}D")

    def _remember_history(self, line: str) -> None:
        if not line.strip():
            return
        if self.history and self.history[-1] == line:
            return
        self.history.append(line)

    def _emit(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    def _emit_block(self, lines: str | list[str]) -> None:
        if isinstance(lines, str):
            rendered = lines.replace("\r\n", "\n").replace("\n", "\r\n")
        else:
            rendered = "\r\n".join(lines)
        self._emit(rendered)


class NetloomShell:
    def __init__(
        self,
        *,
        deps: Any,
        input_func: Callable[[str], str] | None = None,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self.deps = deps
        self.output = output_func
        self.context = ShellContext()
        self.settings = None
        self.plugin = None
        self.catalog: dict[str, Any] | None = None
        self._editor = None if input_func is not None else ShellLineEditor(self)
        self.input = input_func or self._editor.read_line
        self.refresh_state()

    def run(self) -> None:
        profile = self._active_profile()
        plugin_name = self._active_plugin()
        self.output(
            "Entering netloom shell "
            f"(profile: {profile}, plugin: {plugin_name}). "
            "Type ? for help."
        )

        while True:
            try:
                line = self.input(self.prompt())
            except EOFError:
                self.output("")
                return
            except KeyboardInterrupt:
                self.output("")
                continue

            if not self.handle_line(line):
                return

    def prompt(self) -> str:
        path = "netloom"
        if self.context.module:
            path += f"/{self.context.module}"
        if self.context.service:
            path += f"/{self.context.service}"
        return f"{self._active_profile()}:{path}# "

    def handle_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return True

        try:
            tokens = shlex.split(stripped, posix=(os.name != "nt"))
        except ValueError as exc:
            self.output(f"Parse error: {exc}")
            return True

        if not tokens:
            return True

        shell_result = self._handle_shell_builtin(tokens)
        if shell_result is not None:
            return shell_result

        help_requested = False
        filtered_tokens: list[str] = []
        for token in tokens:
            if token == "?":
                help_requested = True
                continue
            filtered_tokens.append(token)
        if help_requested or (filtered_tokens and filtered_tokens[0] == "help"):
            help_tokens = (
                filtered_tokens[1:]
                if filtered_tokens and filtered_tokens[0] == "help"
                else filtered_tokens
            )
            self.show_help(help_tokens)
            return True

        self.execute(filtered_tokens)
        return True

    def execute(self, tokens: list[str], *, absolute: bool = False) -> None:
        absolute_tokens = self._absolute_tokens(tokens, absolute=absolute)
        if not absolute_tokens:
            self.show_help([])
            return

        if self._maybe_navigate(absolute_tokens):
            return

        if absolute_tokens[0] == "shell":
            self.output("Already in netloom shell.")
            return

        try:
            args = self.deps.parse_cli(["netloom", *absolute_tokens])
        except CliParseError as exc:
            self._print_help_error(exc.context, str(exc))
            return

        try:
            self.deps.run_cli(args)
        except KeyboardInterrupt:
            self.output("")
            self.output("Command interrupted.")
        finally:
            self.refresh_state()

    def show_help(self, tokens: list[str], *, absolute: bool = False) -> None:
        absolute_tokens = self._absolute_tokens(tokens, absolute=absolute)
        if not absolute_tokens:
            args = self._context_args()
            self._print_help(args)
            return

        try:
            args = self.deps.parse_cli(["netloom", *absolute_tokens])
        except CliParseError as exc:
            self._print_help_error(exc.context, str(exc))
            return

        self._print_help(args)

    def show_help_for_buffer(self, buffer_text: str) -> None:
        self.show_help(self._tokenize_line(buffer_text))

    def help_text_for_buffer(self, buffer_text: str) -> str:
        return self.help_text_for_tokens(self._tokenize_line(buffer_text))

    def help_text_for_tokens(self, tokens: list[str], *, absolute: bool = False) -> str:
        absolute_tokens = self._absolute_tokens(tokens, absolute=absolute)
        if not absolute_tokens:
            return self._help_text(self._context_args())

        try:
            args = self.deps.parse_cli(["netloom", *absolute_tokens])
        except CliParseError as exc:
            context = exc.context or self._context_args()
            text = self._help_text(context)
            detail = str(exc).strip()
            return f"{text}\n\n{detail}" if detail else text

        return self._help_text(args)

    def completion_candidates(
        self, line: str, *, cursor: int | None = None
    ) -> list[str]:
        current_cursor = len(line) if cursor is None else cursor
        start, _ = _current_token_bounds(line, current_cursor)
        tokens = self._tokenize_fragment(line[:start])
        return self._completion_candidates_for_tokens(tokens)

    def refresh_state(self) -> None:
        try:
            self.settings = self.deps.load_settings()
        except Exception:
            self.settings = None

        self.plugin = None
        plugin_name = self._active_plugin_name()
        if plugin_name and self.settings is not None:
            try:
                self.plugin = self.deps.get_plugin(None, settings=self.settings)
            except ValueError:
                self.plugin = None

        self.catalog = None
        if plugin_name:
            try:
                self.catalog = self.deps.load_cached_catalog_for_plugin(
                    plugin_name,
                    settings=self.settings,
                    catalog_view="visible",
                    prefer_index=False,
                )
            except Exception:
                self.catalog = None

        self._clamp_context()

    def _handle_shell_builtin(self, tokens: list[str]) -> bool | None:
        if tokens[:2] == ["show", "context"] and len(tokens) == 2:
            self.output(f"Profile: {self._active_profile()}")
            self.output(f"Plugin: {self._active_plugin()}")
            self.output(f"Context: {self.prompt().rstrip('# ').strip()}")
            return True

        if tokens == ["top"]:
            self.context = ShellContext()
            return True

        if tokens and tokens[0] == "do":
            if len(tokens) == 1:
                self.output("Usage: do <command>")
                return True
            do_tokens = tokens[1:]
            if do_tokens and do_tokens[0] == "netloom":
                do_tokens = do_tokens[1:]
            self.execute(do_tokens, absolute=True)
            return True

        if tokens == ["quit"]:
            return False

        if tokens == ["exit"]:
            if self.context.service:
                self.context = ShellContext(module=self.context.module)
                return True
            if self.context.module:
                self.context = ShellContext()
                return True
            return False

        return None

    def _print_help(self, args: dict[str, Any]) -> None:
        self.output(self._help_text(args))

    def _help_text(self, args: dict[str, Any]) -> str:
        plugin_marker = self.plugin
        if plugin_marker is None and self._active_plugin_name():
            plugin_marker = object()
        return self.deps.render_help(
            self.catalog,
            args,
            version=self.deps.get_version(),
            plugin=plugin_marker,
        )

    def _print_help_error(self, context: dict[str, Any] | None, message: str) -> None:
        self._print_help(context or self._context_args())
        detail = message.strip()
        if detail:
            self.output("")
            self.output(detail)

    def _context_args(self) -> dict[str, Any]:
        args: dict[str, Any] = {}
        if self.context.module:
            args["module"] = self.context.module
        if self.context.service:
            args["service"] = self.context.service
        return args

    def _active_profile_name(self) -> str | None:
        return getattr(self.settings, "active_profile", None)

    def _active_plugin_name(self) -> str | None:
        return getattr(self.settings, "plugin", None)

    def _active_profile(self) -> str:
        return self._active_profile_name() or "no-profile"

    def _active_plugin(self) -> str:
        return self._active_plugin_name() or "<unset>"

    def _module_names(self) -> set[str]:
        modules = (self.catalog or {}).get("modules") or {}
        return set(modules.keys()) if isinstance(modules, dict) else set()

    def _service_names(self, module: str) -> set[str]:
        services = display_services_for_module(self.catalog, module)
        return set(services.keys())

    def _action_names(self, module: str, service: str) -> set[str]:
        entry = resolve_service_entry(self.catalog, module, service)
        if not isinstance(entry, dict):
            return set()
        return set(service_cli_actions(entry))

    def _absolute_tokens(
        self, tokens: list[str], *, absolute: bool = False
    ) -> list[str]:
        if absolute or not tokens:
            return list(tokens)

        first = tokens[0]
        modules = self._module_names()
        if first in _GLOBAL_BUILTINS or first in modules:
            return list(tokens)

        if self.context.module:
            services = self._service_names(self.context.module)
            if first in services:
                return [self.context.module, *tokens]
            if self.context.service:
                actions = self._action_names(self.context.module, self.context.service)
                if first in actions:
                    return [self.context.module, self.context.service, *tokens]
                return [self.context.module, self.context.service, *tokens]
            return [self.context.module, *tokens]

        return list(tokens)

    def _maybe_navigate(self, absolute_tokens: list[str]) -> bool:
        if not absolute_tokens or any(
            token.startswith("-") for token in absolute_tokens
        ):
            return False

        modules = self._module_names()
        if len(absolute_tokens) == 1 and absolute_tokens[0] in modules:
            self.context = ShellContext(module=absolute_tokens[0])
            return True

        if len(absolute_tokens) == 2 and absolute_tokens[0] in modules:
            services = self._service_names(absolute_tokens[0])
            if absolute_tokens[1] in services:
                self.context = ShellContext(
                    module=absolute_tokens[0],
                    service=absolute_tokens[1],
                )
                return True

        return False

    def _clamp_context(self) -> None:
        if not self.context.module:
            return
        if self.context.module not in self._module_names():
            self.context = ShellContext()
            return
        if self.context.service and self.context.service not in self._service_names(
            self.context.module
        ):
            self.context = ShellContext(module=self.context.module)

    def _completion_candidates_for_tokens(self, tokens: list[str]) -> list[str]:
        if tokens and tokens[0] == "show":
            return ["context"] if len(tokens) <= 1 else []

        if tokens and tokens[0] == "do":
            return self._root_completion_candidates(tokens[1:], include_shell=False)

        if tokens and (
            tokens[0] in _GLOBAL_BUILTINS or tokens[0] in self._module_names()
        ):
            return self._root_completion_candidates(tokens)

        if self.context.service:
            return self._service_completion_candidates(tokens)
        if self.context.module:
            return self._module_completion_candidates(tokens)
        return self._root_completion_candidates(tokens)

    def _root_completion_candidates(
        self, tokens: list[str], *, include_shell: bool = True
    ) -> list[str]:
        candidates = cli_completion_candidates(tokens, self.catalog)
        if not tokens:
            extras = sorted(_SHELL_BUILTINS)
            if include_shell:
                return sorted(set([*candidates, *extras]))
            return candidates
        if tokens[0] == "show":
            return ["context"] if len(tokens) <= 1 else []
        if include_shell and tokens[0] in _SHELL_BUILTINS:
            return sorted(set([*candidates, *_SHELL_BUILTINS]))
        return candidates

    def _module_completion_candidates(self, tokens: list[str]) -> list[str]:
        module = self.context.module
        if module is None:
            return self._root_completion_candidates(tokens)
        services = sorted(self._service_names(module))
        if not tokens:
            return sorted([*services, "do", "exit", "quit", "show", "top"])
        if tokens[0] in _GLOBAL_BUILTINS or tokens[0] in self._module_names():
            return self._root_completion_candidates(tokens)
        if tokens[0] == "show":
            return ["context"] if len(tokens) <= 1 else []
        if tokens[0] in _SHELL_BUILTINS:
            return sorted([*services, "do", "exit", "quit", "show", "top"])
        if tokens[0] in self._service_names(module):
            return cli_completion_candidates([module, *tokens], self.catalog)
        return services

    def _service_completion_candidates(self, tokens: list[str]) -> list[str]:
        module = self.context.module
        service = self.context.service
        if module is None or service is None:
            return self._module_completion_candidates(tokens)
        actions = sorted(self._action_names(module, service))
        if not tokens:
            return sorted([*actions, "do", "exit", "quit", "show", "top"])
        if tokens[0] in _GLOBAL_BUILTINS or tokens[0] in self._module_names():
            return self._root_completion_candidates(tokens)
        if tokens[0] == "show":
            return ["context"] if len(tokens) <= 1 else []
        if tokens[0] in _SHELL_BUILTINS:
            return sorted([*actions, "do", "exit", "quit", "show", "top"])
        if tokens[0] in actions:
            return cli_completion_candidates([module, service, *tokens], self.catalog)
        sibling_services = sorted(self._service_names(module))
        return sorted([*actions, *sibling_services])

    def _tokenize_line(self, line: str) -> list[str]:
        stripped = line.strip()
        if not stripped:
            return []
        try:
            return shlex.split(stripped, posix=(os.name != "nt"))
        except ValueError:
            return stripped.split()

    def _tokenize_fragment(self, fragment: str) -> list[str]:
        if not fragment.strip():
            return []
        try:
            return shlex.split(fragment, posix=(os.name != "nt"))
        except ValueError:
            return fragment.split()


def _current_token_bounds(text: str, cursor: int) -> tuple[int, int]:
    start = cursor
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    end = cursor
    while end < len(text) and not text[end].isspace():
        end += 1
    return start, end


def handle_shell_command(args: dict, *, deps: Any) -> bool:
    if args.get("module") != "shell":
        return False
    if args.get("service") or args.get("action"):
        return False
    NetloomShell(deps=deps).run()
    return True


__all__ = [
    "NetloomShell",
    "ShellContext",
    "ShellLineEditor",
    "handle_shell_command",
]
