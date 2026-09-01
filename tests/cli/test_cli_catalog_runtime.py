from __future__ import annotations

from netloom.cli import catalog_runtime


def test_get_catalog_for_cli_falls_back_when_timing_sink_is_unsupported():
    plugin = type(
        "Plugin",
        (),
        {
            "get_api_catalog": staticmethod(
                lambda cp, *, token, force_refresh=False, settings=None, catalog_view="visible": {  # noqa: E501
                    "modules": {}
                }
            )
        },
    )()

    catalog = catalog_runtime.get_catalog_for_cli(
        plugin,
        object(),
        token="token",
        settings=None,
        force_refresh=True,
        catalog_view="visible",
        timing_sink=lambda *args: None,
    )

    assert catalog == {"modules": {}}


def test_print_help_uses_injected_version(capsys):
    captured: dict[str, str] = {}

    class _Deps:
        def _env_cli_timing_value(self):
            return None

        def load_interactive_settings(self):
            return None

        def _import_help_layer(self):
            return None

        def render_help(self, catalog, args, *, version, plugin):
            captured["version"] = version
            return "help text"

        def get_version(self):
            return "3.2.1"

    catalog_runtime.print_help({"module": "server"}, deps=_Deps())

    assert capsys.readouterr().out.strip() == "help text"
    assert captured["version"] == "3.2.1"
