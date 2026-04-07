from __future__ import annotations

from netloom.cli.telemetry import CacheUpdateProgressReporter, CliProfiler


def test_cli_profiler_emits_timing_summary(capsys):
    profiler = CliProfiler("demo", env_value="1")

    profiler.call("work", lambda: None)
    profiler.emit()

    err = capsys.readouterr().err
    assert "[netloom timing] demo total=" in err
    assert "work=" in err


def test_cache_update_progress_reporter_emits_progress_messages(capsys):
    reporter = CacheUpdateProgressReporter()

    reporter.stage("building client")
    reporter("done")

    err = capsys.readouterr().err
    assert "[netloom progress] building client" in err
    assert "[netloom progress] cache update complete" in err
