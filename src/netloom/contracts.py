from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class NetloomRequest:
    """Neutral request passed from user interfaces into Netloom core."""

    module: str | None = None
    service: str | None = None
    action: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    plugin: str | None = None
    source: str = "cli"

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", dict(self.arguments))

    @classmethod
    def from_mapping(
        cls, values: Mapping[str, Any], *, source: str = "cli"
    ) -> "NetloomRequest":
        arguments = dict(values)
        module = arguments.pop("module", None)
        service = arguments.pop("service", None)
        action = arguments.pop("action", None)
        plugin = arguments.pop("plugin", None)
        return cls(
            module=module,
            service=service,
            action=action,
            arguments=arguments,
            plugin=plugin,
            source=source,
        )

    def to_mapping(self) -> dict[str, Any]:
        values = dict(self.arguments)
        if self.module is not None:
            values["module"] = self.module
        if self.service is not None:
            values["service"] = self.service
        if self.action is not None:
            values["action"] = self.action
        if self.plugin is not None:
            values["plugin"] = self.plugin
        return values


@dataclass(frozen=True)
class ExecutionOptions:
    """Cross-interface execution options derived from CLI, GUI, or API callers."""

    catalog_view: str = "visible"
    output_format: str | None = None
    output_path: str | None = None
    console: bool = False
    mask_secrets: bool = True
    dry_run: bool = False
    continue_on_error: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", dict(self.extra))


@dataclass(frozen=True)
class NetloomResult:
    """Netloom-level result returned from core to a user interface."""

    data: Any = None
    status: str = "ok"
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "artifacts", dict(self.artifacts))

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class HttpRequest:
    """Generic HTTP request built by plugins and executed by HTTP transport."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    json_body: Any = None
    body: bytes | str | None = None
    timeout: float | None = None
    verify_ssl: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", self.method.upper())
        object.__setattr__(self, "headers", dict(self.headers))
        object.__setattr__(self, "params", dict(self.params))


@dataclass(frozen=True)
class HttpResponse:
    """Transport-owned HTTP response independent of a concrete HTTP library."""

    status_code: int
    reason: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    url: str | None = None
    request: HttpRequest | None = None
    content_type: str = ""
    filename: str | None = None
    is_binary: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", dict(self.headers))

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def content(self) -> bytes:
        return self.body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


@dataclass(frozen=True)
class PluginExecutionContext:
    """Runtime context supplied by core when dispatching work to a plugin."""

    settings: Any
    options: ExecutionOptions = field(default_factory=ExecutionOptions)
    token: str | None = None
    catalog: dict[str, Any] | None = None
    http_client: Any = None

    def __post_init__(self) -> None:
        if self.catalog is not None:
            object.__setattr__(self, "catalog", dict(self.catalog))


@dataclass(frozen=True)
class PluginDefinition:
    """Current runtime plugin contract.

    This intentionally mirrors the existing plugin surface so v2 contract work can
    start without changing command behavior.
    """

    name: str
    display_name: str
    build_client: Callable[..., Any]
    resolve_auth_token: Callable[..., str]
    get_api_catalog: Callable[..., dict[str, Any]]
    load_cached_catalog: Callable[..., dict[str, Any] | None]
    clear_api_cache: Callable[..., bool]
    normalize_copy_payload: Callable[..., dict[str, Any]]
    restore_secret_fields: Callable[..., Any]
    preflight_error_for_payload: Callable[..., str | None]
    prepare_write_payload: Callable[..., Any] | None = None
    load_cached_index: Callable[..., dict[str, Any] | None] | None = None
    help_context: Callable[[], dict[str, Any]] | None = None
    normalize_diff_item: Callable[..., Any] | None = None


@runtime_checkable
class Plugin(Protocol):
    name: str
    display_name: str
    build_client: Callable[..., Any]
    resolve_auth_token: Callable[..., str]
    get_api_catalog: Callable[..., dict[str, Any]]
    load_cached_catalog: Callable[..., dict[str, Any] | None]
    clear_api_cache: Callable[..., bool]
    normalize_copy_payload: Callable[..., dict[str, Any]]
    restore_secret_fields: Callable[..., Any]
    preflight_error_for_payload: Callable[..., str | None]


@runtime_checkable
class ExecutablePlugin(Plugin, Protocol):
    def execute(
        self,
        request: NetloomRequest,
        context: PluginExecutionContext,
    ) -> NetloomResult: ...


__all__ = [
    "ExecutablePlugin",
    "ExecutionOptions",
    "HttpRequest",
    "HttpResponse",
    "NetloomRequest",
    "NetloomResult",
    "Plugin",
    "PluginDefinition",
    "PluginExecutionContext",
]
