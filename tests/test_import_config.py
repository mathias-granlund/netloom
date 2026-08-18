from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

import netloom.cli.import_config as import_config
from netloom.cli.import_config import (
    ConfigCommand,
    build_import_plan,
    handle_import_command,
    import_running_config,
    parse_running_config,
)
from netloom.core.config import AppPaths, Settings


def _settings(tmp_path: Path) -> Settings:
    paths = AppPaths(
        cache_dir=tmp_path / "cache",
        state_dir=tmp_path / "state",
        response_dir=tmp_path / "responses",
        app_log_dir=tmp_path / "logs",
    ).ensure()
    return Settings(
        server="clearpass.example",
        active_profile="lab",
        plugin="clearpass",
        paths=paths,
    )


def _catalog(*, delete: bool = True, replace: bool = True):
    actions = {
        "add": {
            "method": "POST",
            "paths": ["/api/network-device"],
            "body_fields": [
                {"name": "name", "required": True},
                {"name": "ip_address", "required": False},
                {"name": "radius_secret", "required": False},
            ],
        },
        "update": {
            "method": "PATCH",
            "paths": ["/api/network-device/{id}"],
            "params": ["id"],
            "body_fields": [
                {"name": "name", "required": False},
                {"name": "ip_address", "required": False},
                {"name": "radius_secret", "required": False},
            ],
        },
    }
    if replace:
        actions["replace"] = {
            "method": "PUT",
            "paths": ["/api/network-device/{id}"],
            "params": ["id"],
            "body_fields": [
                {"name": "name", "required": True},
                {"name": "ip_address", "required": False},
                {"name": "radius_secret", "required": False},
            ],
        }
    if delete:
        actions["delete"] = {
            "method": "DELETE",
            "paths": ["/api/network-device/{id}"],
            "params": ["id"],
        }
    return {
        "modules": {
            "policyelements": {
                "network-device": {
                    "actions": actions,
                }
            }
        }
    }


def _service_catalog():
    service_fields = [
        {"name": "name", "required": True},
        {"name": "template", "required": True},
        {"name": "enabled", "required": False},
        {"name": "order_no", "required": False},
        {"name": "enf_policy", "required": True},
    ]
    return {
        "modules": {
            "policyelements": {
                "config-service": {
                    "actions": {
                        "add": {
                            "method": "POST",
                            "paths": ["/api/config/service"],
                            "body_fields": service_fields,
                        },
                        "replace": {
                            "method": "PUT",
                            "paths": [
                                "/api/config/service/{id}",
                                "/api/config/service/name/{services_name}",
                            ],
                            "params": ["id", "services_name"],
                            "body_fields": service_fields,
                        },
                        "delete": {
                            "method": "DELETE",
                            "paths": [
                                "/api/config/service/{id}",
                                "/api/config/service/name/{services_name}",
                            ],
                            "params": ["id", "services_name"],
                        },
                    },
                },
                "config-service-reorder": {
                    "actions": {
                        "update": {
                            "method": "PATCH",
                            "paths": ["/api/config/service/reorder"],
                            "params": ["service_orders"],
                            "body_fields": [
                                {"name": "service_orders", "required": True},
                            ],
                        }
                    },
                },
                "enforcement-policy": {
                    "actions": {
                        "add": {
                            "method": "POST",
                            "paths": ["/api/enforcement-policy"],
                            "body_fields": [
                                {"name": "name", "required": True},
                                {"name": "enforcement_type", "required": True},
                                {"name": "default_enforcement_profile"},
                                {"name": "rule_eval_algo"},
                                {"name": "rules"},
                            ],
                        },
                        "delete": {
                            "method": "DELETE",
                            "paths": ["/api/enforcement-policy/name/{name}"],
                            "params": ["name"],
                        },
                    },
                },
            }
        }
    }


class _CP:
    def __init__(self):
        self.calls: list[dict] = []

    def get_action_definition(self, api_catalog, module, service, action):
        return api_catalog["modules"][module][service]["actions"][action]

    def resolve_action(self, api_catalog, module, service, action, args):
        action_def = self.get_action_definition(api_catalog, module, service, action)
        path = action_def["paths"][0]
        placeholders = [
            part.split("}", 1)[0] for part in path.split("{")[1:] if "}" in part
        ]
        missing = [name for name in placeholders if args.get(name) in (None, "")]
        if missing:
            joined = ", ".join(f"--{name}=..." for name in missing)
            raise ValueError(f"Missing required path variables: {joined}")
        return action_def, path, placeholders

    def add(self, api_catalog, token, args, payload):
        self.calls.append(
            {
                "action": "add",
                "api_catalog": api_catalog,
                "token": token,
                "args": dict(args),
                "payload": payload,
            }
        )
        return {"id": 8, **payload}

    def replace(self, api_catalog, token, args, payload):
        self.calls.append(
            {
                "action": "replace",
                "api_catalog": api_catalog,
                "token": token,
                "args": dict(args),
                "payload": payload,
            }
        )
        return {"id": args["id"], **payload}

    def update(self, api_catalog, token, args, payload):
        self.calls.append(
            {
                "action": "update",
                "api_catalog": api_catalog,
                "token": token,
                "args": dict(args),
                "payload": payload,
            }
        )
        response = dict(payload)
        if "id" in args:
            response["id"] = args["id"]
        return response

    def delete(self, api_catalog, token, args, *, params=None):
        self.calls.append(
            {
                "action": "delete",
                "api_catalog": api_catalog,
                "token": token,
                "args": dict(args),
                "params": params,
            }
        )
        return {
            "deleted": args.get("id")
            or args.get("name")
            or args.get("services_name")
        }


def _plugin(cp, *, preflight=None):
    return types.SimpleNamespace(
        name="clearpass",
        build_client=lambda settings, mask_secrets=True: cp,
        resolve_auth_token=lambda cp, settings: "token",
        preflight_error_for_payload=preflight
        or (lambda module, service, action, payload: None),
    )


def _command(line_no, payload, *, source_id=7, action="add", **extra):
    return ConfigCommand(
        line_no=line_no,
        text=f"netloom policyelements network-device {action}",
        args={
            "module": "policyelements",
            "service": "network-device",
            "action": action,
            "payload_json": json.dumps(payload),
            **extra,
        },
        source_identity={"id": source_id} if source_id is not None else {},
    )


def _config_texts(*entries: tuple[int, dict]) -> str:
    lines = ["# netloom running-config"]
    for source_id, payload in entries:
        lines.extend(
            [
                f"# source-id: {source_id}",
                (
                    "netloom policyelements network-device add "
                    f"--payload-json={json.dumps(json.dumps(payload))}"
                ),
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _config_text(payload: dict, *, source_id=7) -> str:
    return _config_texts((source_id, payload))


def _network_device_config(name: str, ip_address: str) -> dict:
    return {"name": name, "ip_address": ip_address}


def _service_payload(
    name: str,
    order_no: int,
    *,
    enabled: bool = True,
    enf_policy: str = "Allow Access",
) -> dict:
    return {
        "name": name,
        "template": "802.1X Wired",
        "enabled": enabled,
        "order_no": order_no,
        "enf_policy": enf_policy,
    }


def _service_command(line_no: int, source_id: int, payload: dict) -> ConfigCommand:
    return ConfigCommand(
        line_no=line_no,
        text="netloom policyelements config-service add",
        args={
            "module": "policyelements",
            "service": "config-service",
            "action": "add",
            "payload_json": json.dumps(payload),
        },
        source_identity={"id": source_id},
    )


def _enforcement_policy_command(
    line_no: int,
    source_id: int,
    name: str,
) -> ConfigCommand:
    return ConfigCommand(
        line_no=line_no,
        text="netloom policyelements enforcement-policy add",
        args={
            "module": "policyelements",
            "service": "enforcement-policy",
            "action": "add",
            "payload_json": json.dumps(
                {
                    "name": name,
                    "enforcement_type": "RADIUS",
                    "default_enforcement_profile": "[Deny Access Profile]",
                    "rule_eval_algo": "first-applicable",
                    "rules": [],
                }
            ),
        },
        source_identity={"id": source_id},
    )


def test_parse_running_config_reads_replay_commands_with_source_identity(tmp_path):
    path = tmp_path / "running-config.txt"
    path.write_text(
        "\n".join(
            [
                "# netloom running-config",
                "",
                "# source-id: 7",
                (
                    "netloom policyelements network-device add "
                    '--payload-json=\'{"name":"switch a",'
                    '"ip_address":"192.0.2.10"}\''
                ),
            ]
        ),
        encoding="utf-8",
    )

    commands = parse_running_config(path)

    assert len(commands) == 1
    assert commands[0].line_no == 4
    assert commands[0].source_identity == {"id": 7}
    assert commands[0].args["module"] == "policyelements"
    assert commands[0].args["service"] == "network-device"
    assert commands[0].args["action"] == "add"
    assert json.loads(commands[0].args["payload_json"]) == {
        "name": "switch a",
        "ip_address": "192.0.2.10",
    }


def test_parse_running_config_rejects_non_netloom_lines(tmp_path):
    path = tmp_path / "running-config.txt"
    path.write_text("echo nope\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 1: expected a netloom command"):
        parse_running_config(path)


def test_parse_running_config_rejects_read_only_commands(tmp_path):
    path = tmp_path / "running-config.txt"
    path.write_text(
        "netloom policyelements network-device list\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="only importable mutation actions"):
        parse_running_config(path)


def test_import_plan_marks_identical_current_object_unchanged_without_preflight(
    tmp_path,
):
    cp = _CP()
    payload = {"name": "switch-a", "ip_address": "192.0.2.10"}
    desired = [_command(3, payload)]
    current = [_command(3, payload)]

    def preflight(module, service, action, payload):
        raise AssertionError("unchanged objects should not run write preflight")

    plan = build_import_plan(
        _plugin(cp, preflight=preflight),
        cp,
        "token",
        _catalog(),
        desired,
        current,
        settings=_settings(tmp_path),
    )

    assert cp.calls == []
    assert plan == [
        {
            "line": 3,
            "module": "policyelements",
            "service": "network-device",
            "label": "switch-a",
            "operation": "none",
            "status": "unchanged",
            "match_key": ["policyelements", "network-device", "id", "7"],
        }
    ]


def test_import_plan_ignores_non_restorable_scopes(tmp_path):
    cp = _CP()
    payload = {"name": "switch-a", "ip_address": "192.0.2.10"}
    desired = [
        ConfigCommand(
            line_no=2,
            text="netloom logs system-event add",
            args={
                "module": "logs",
                "service": "system-event",
                "action": "add",
                "payload_json": '{"source":"system","description":"event"}',
            },
        ),
        ConfigCommand(
            line_no=3,
            text="netloom globalserverconfiguration messaging-setup add",
            args={
                "module": "globalserverconfiguration",
                "service": "messaging-setup",
                "action": "add",
                "payload_json": '{"server_name":"smtp.example","password":"******"}',
            },
        ),
        _command(4, payload),
    ]
    current = [_command(4, payload)]

    plan = build_import_plan(
        _plugin(cp),
        cp,
        "token",
        _catalog(),
        desired,
        current,
        settings=_settings(tmp_path),
    )

    assert len(plan) == 1
    assert plan[0]["module"] == "policyelements"
    assert plan[0]["status"] == "unchanged"


def test_import_running_config_dry_run_plans_replace_for_changed_match(tmp_path):
    cp = _CP()
    desired = [_command(3, {"name": "switch-a", "ip_address": "192.0.2.11"})]
    current = [_command(3, {"name": "switch-a", "ip_address": "192.0.2.10"})]

    report = import_running_config(
        _plugin(cp),
        cp,
        "token",
        _catalog(),
        desired,
        current,
        source="running-config.txt",
        settings=_settings(tmp_path),
        dry_run=True,
    )

    assert cp.calls == []
    assert report["summary"]["planned"] == 1
    assert report["summary"]["replace"] == 1
    assert report["items"][0]["status"] == "planned"
    assert report["items"][0]["operation"] == "replace"
    assert (
        "netloom policyelements network-device replace --id=7"
        in report["items"][0]["command"]
    )


def test_import_running_config_restores_config_service_with_single_reorder(
    tmp_path,
):
    cp = _CP()
    desired = [
        _service_command(10, 1001, _service_payload("service-a", 1)),
        _service_command(12, 1002, _service_payload("deleted-service", 2)),
        _service_command(14, 1003, _service_payload("service-b", 3)),
    ]
    current = [
        _service_command(10, 1001, _service_payload("service-a", 1)),
        _service_command(14, 1003, _service_payload("service-b", 2)),
    ]

    report = import_running_config(
        _plugin(cp),
        cp,
        "token",
        _service_catalog(),
        desired,
        current,
        source="running-config.txt",
        settings=_settings(tmp_path),
        dry_run=True,
    )

    assert cp.calls == []
    assert report["summary"]["planned"] == 2
    assert report["summary"]["create"] == 1
    assert report["summary"]["update"] == 1
    assert report["summary"]["replace"] == 0

    planned = [item for item in report["items"] if item["status"] == "planned"]
    assert [item["operation"] for item in planned] == ["add", "update"]
    assert planned[0]["label"] == "deleted-service"
    assert "order_no" not in planned[0]["command"]
    assert (
        "netloom policyelements config-service delete "
        "--services-name=deleted-service"
    ) in planned[0]["rollback_command"]
    assert planned[1]["service"] == "config-service-reorder"
    assert planned[1]["label"] == "config-service order"
    assert '"service_name":"deleted-service","order_no":2' in planned[1]["command"]
    assert '"service_name":"service-b","order_no":3' in planned[1]["command"]


def test_import_running_config_orders_dependencies_before_config_services(
    tmp_path,
):
    cp = _CP()
    desired = [
        _service_command(
            30,
            3001,
            _service_payload(
                "MG_prefix_802.1X_Service",
                3,
                enf_policy="MG_Prefix_Enforcement_Policy",
            ),
        ),
        _enforcement_policy_command(
            40,
            4001,
            "MG_Prefix_Enforcement_Policy",
        ),
    ]

    report = import_running_config(
        _plugin(cp),
        cp,
        "token",
        _service_catalog(),
        desired,
        [],
        source="running-config.txt",
        settings=_settings(tmp_path),
        dry_run=True,
    )

    planned = [item for item in report["items"] if item["status"] == "planned"]
    assert [
        (item["module"], item["service"], item["label"], item["operation"])
        for item in planned
    ] == [
        (
            "policyelements",
            "enforcement-policy",
            "MG_Prefix_Enforcement_Policy",
            "add",
        ),
        (
            "policyelements",
            "config-service",
            "MG_prefix_802.1X_Service",
            "add",
        ),
        (
            "policyelements",
            "config-service-reorder",
            "config-service order",
            "update",
        ),
    ]


def test_import_running_config_executes_replace_for_changed_match(tmp_path):
    cp = _CP()
    desired = [_command(3, {"name": "switch-a", "ip_address": "192.0.2.11"})]
    current = [_command(3, {"name": "switch-a", "ip_address": "192.0.2.10"})]

    report = import_running_config(
        _plugin(cp),
        cp,
        "token",
        _catalog(),
        desired,
        current,
        source="running-config.txt",
        settings=_settings(tmp_path),
    )

    assert [call["action"] for call in cp.calls] == ["replace"]
    assert cp.calls[0]["args"]["id"] == 7
    assert cp.calls[0]["payload"] == {
        "name": "switch-a",
        "ip_address": "192.0.2.11",
    }
    assert report["summary"]["applied"] == 1
    assert report["summary"]["replace"] == 1


def test_import_running_config_skips_unreversible_create_without_delete(tmp_path):
    cp = _CP()
    desired = [_command(3, {"name": "switch-a"}, source_id=None)]

    report = import_running_config(
        _plugin(cp),
        cp,
        "token",
        _catalog(delete=False),
        desired,
        [],
        source="running-config.txt",
        settings=_settings(tmp_path),
    )

    assert cp.calls == []
    assert report["summary"]["skipped"] == 1
    assert report["items"][0]["reason"] == (
        "create is not reversible because delete is unavailable"
    )


def test_handle_import_command_exports_current_and_writes_report(
    tmp_path, capsys, monkeypatch
):
    settings = Settings(
        **{
            **vars(_settings(tmp_path)),
            "running_config_exclude": "globalserverconfiguration/messaging-setup",
        }
    )
    cp = _CP()
    config_path = tmp_path / "running-config.txt"
    report_path = tmp_path / "import-report.json"
    desired_text = _config_texts(
        (7, _network_device_config("switch-a", "192.0.2.10")),
        (8, _network_device_config("switch-b", "192.0.2.11")),
    )
    current_text = _config_texts(
        (7, _network_device_config("switch-a", "192.0.2.10")),
        (8, _network_device_config("switch-b", "192.0.2.12")),
    )
    config_path.write_text(desired_text, encoding="utf-8")

    def render_current(*args, **kwargs):
        assert kwargs["exclude"] == {("logs", None)}
        return current_text

    monkeypatch.setattr(import_config, "render_running_config", render_current)
    deps = types.SimpleNamespace(
        _catalog_view_from_args=lambda args: "visible",
        _get_catalog_for_cli=lambda plugin, cp, **kwargs: _catalog(),
    )

    handled = handle_import_command(
        {
            "module": "import",
            "file": str(config_path),
            "out": str(report_path),
            "dry_run": True,
            "exclude": "logs",
        },
        plugin=_plugin(cp),
        settings=settings,
        deps=deps,
    )

    assert handled is True
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["unchanged"] == 1
    assert report["summary"]["planned"] == 1
    assert len(report["items"]) == 1
    assert report["items"][0]["label"] == "switch-b"
    assert report["items"][0]["operation"] == "replace"
    assert report["items"][0]["status"] == "planned"
    out = capsys.readouterr().out
    assert "Import dry run" in out
    assert "Unchanged: 1" in out
    assert "Planned: 1" in out
