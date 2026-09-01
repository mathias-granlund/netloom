from netloom.contracts import (
    ExecutablePlugin,
    ExecutionOptions,
    HttpRequest,
    HttpResponse,
    NetloomRequest,
    NetloomResult,
    Plugin,
    PluginDefinition,
)
from netloom.core.plugin_registry import PluginDefinition as CorePluginDefinition


def test_netloom_request_round_trips_legacy_arg_mapping():
    args = {
        "module": "policyelements",
        "service": "network-device",
        "action": "list",
        "limit": "50",
        "console": True,
        "plugin": "clearpass",
    }

    request = NetloomRequest.from_mapping(args)

    assert request.module == "policyelements"
    assert request.service == "network-device"
    assert request.action == "list"
    assert request.plugin == "clearpass"
    assert request.arguments == {"limit": "50", "console": True}
    assert request.to_mapping() == args


def test_contracts_copy_mutable_mapping_inputs():
    args = {"limit": "25"}
    request = NetloomRequest(arguments=args)
    args["limit"] = "100"

    assert request.arguments == {"limit": "25"}

    options_extra = {"hydrate": "auto"}
    options = ExecutionOptions(extra=options_extra)
    options_extra["hydrate"] = "never"

    assert options.extra == {"hydrate": "auto"}


def test_http_request_normalizes_method_and_copies_mappings():
    headers = {"accept": "application/json"}
    params = {"limit": 25}

    request = HttpRequest(
        method="get",
        url="https://example.test/api/items",
        headers=headers,
        params=params,
    )
    headers["authorization"] = "Bearer token"
    params["limit"] = 50

    assert request.method == "GET"
    assert request.headers == {"accept": "application/json"}
    assert request.params == {"limit": 25}


def test_http_response_ok_status_is_transport_based():
    assert HttpResponse(status_code=204).ok is True
    assert HttpResponse(status_code=404).ok is False


def test_netloom_result_ok_status_is_domain_based():
    assert NetloomResult(data={"id": 1}).ok is True
    assert NetloomResult(status="error", message="failed").ok is False


def test_plugin_definition_remains_available_from_core_plugin_module():
    assert CorePluginDefinition is PluginDefinition


def test_plugin_definition_satisfies_current_plugin_protocol():
    plugin = PluginDefinition(
        name="example",
        display_name="Example",
        build_client=lambda *args, **kwargs: object(),
        resolve_auth_token=lambda *args, **kwargs: "token",
        get_api_catalog=lambda *args, **kwargs: {},
        load_cached_catalog=lambda *args, **kwargs: None,
        clear_api_cache=lambda *args, **kwargs: True,
        normalize_copy_payload=lambda *args, **kwargs: {},
        restore_secret_fields=lambda *args, **kwargs: None,
        preflight_error_for_payload=lambda *args, **kwargs: None,
    )

    assert isinstance(plugin, Plugin)


def test_plugin_definition_is_not_yet_the_future_executable_plugin_contract():
    plugin = PluginDefinition(
        name="example",
        display_name="Example",
        build_client=lambda *args, **kwargs: object(),
        resolve_auth_token=lambda *args, **kwargs: "token",
        get_api_catalog=lambda *args, **kwargs: {},
        load_cached_catalog=lambda *args, **kwargs: None,
        clear_api_cache=lambda *args, **kwargs: True,
        normalize_copy_payload=lambda *args, **kwargs: {},
        restore_secret_fields=lambda *args, **kwargs: None,
        preflight_error_for_payload=lambda *args, **kwargs: None,
    )

    assert not isinstance(plugin, ExecutablePlugin)
