from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netloom.core.config import Settings


class CliProfiler:
    def __init__(
        self,
        label: str,
        *,
        settings: Settings | None = None,
        env_value: str | None = None,
        allow_settings_fallback: bool = True,
    ):
        self.label = label
        if env_value is not None:
            self.enabled = env_value.strip().lower() not in {"", "0", "false", "no"}
        elif allow_settings_fallback:
            self.enabled = bool(getattr(settings, "cli_timing", False))
        else:
            self.enabled = False
        self.records: list[tuple[str, float]] = []
        self._start = time.perf_counter()

    def add_record(self, name: str, duration_ms: float) -> None:
        if not self.enabled:
            return
        self.records.append((name, duration_ms))

    def call(self, name: str, func, *args, **kwargs):
        if not self.enabled:
            return func(*args, **kwargs)
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            self.records.append((name, (time.perf_counter() - started) * 1000.0))

    def emit(self) -> None:
        if not self.enabled:
            return
        total_ms = (time.perf_counter() - self._start) * 1000.0
        aggregated: dict[str, float] = {}
        for name, duration in self.records:
            aggregated[name] = aggregated.get(name, 0.0) + duration
        parts = [f"{name}={duration:.1f}ms" for name, duration in aggregated.items()]
        summary = ", ".join(parts)
        print(
            f"[netloom timing] {self.label} total={total_ms:.1f}ms"
            + (f" ({summary})" if summary else ""),
            file=sys.stderr,
        )


class CacheUpdateProgressReporter:
    def __init__(self):
        self._last_subdocument_count = 0

    def _print(self, message: str) -> None:
        print(f"[netloom progress] {message}", file=sys.stderr)

    def _progress_text(self, current, total) -> str:
        if not isinstance(current, int) or not isinstance(total, int) or total <= 0:
            return f"{current}/{total}"
        percent = round((current / total) * 100)
        return f"{current}/{total} ({percent}%)"

    def stage(self, message: str) -> None:
        self._print(message)

    def __call__(self, event: str, **data) -> None:
        if event == "fetch_api_docs":
            self._print("fetching /api-docs")
            return
        if event == "fetch_effective_privileges":
            self._print("fetching effective privileges")
            return
        if event == "module_listing":
            current = data.get("current")
            total = data.get("total")
            module = data.get("module")
            self._print(
                f"fetching module listing {self._progress_text(current, total)}: "
                f"{module}"
            )
            return
        if event == "subdocuments_start":
            total = data.get("total")
            self._print(f"fetching subdocuments: {self._progress_text(0, total)}")
            self._last_subdocument_count = 0
            return
        if event == "subdocument":
            current = int(data.get("current", 0))
            total = int(data.get("total", 0))
            module = data.get("module")
            if (
                total <= 10
                or current in {1, total}
                or current - self._last_subdocument_count >= 10
            ):
                self._print(
                    f"fetching subdocuments: {self._progress_text(current, total)} "
                    f"({module})"
                )
                self._last_subdocument_count = current
            return
        if event == "build_catalog":
            self._print("building catalog")
            return
        if event == "write_full_cache":
            self._print("writing full cache")
            return
        if event == "write_fast_index":
            self._print("writing fast index")
            return
        if event == "done":
            self._print("cache update complete")
