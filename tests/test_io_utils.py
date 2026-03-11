import json

import pytest

from arapy.io.files import load_api_token_file, load_payload_file
from arapy.io.output import _extract_by_path, log_to_file, sanitize_secrets


def test_extract_by_path_happy():
    data = {"a": {"b": [{"c": 3}]}}
    assert _extract_by_path(data, ("a", "b", 0, "c")) == 3


def test_log_to_file_rejects_bad_mode(tmp_path):
    with pytest.raises(ValueError, match="mode must be"):
        log_to_file({"x": 1}, filename=tmp_path / "x.json", mode="x")


def test_log_to_file_rejects_bad_format(tmp_path):
    with pytest.raises(ValueError, match="data_format must be"):
        log_to_file({"x": 1}, filename=tmp_path / "x.bad", data_format="xml")


def test_log_to_file_json_writes_and_console(tmp_path, capsys):
    out = tmp_path / "out.json"
    value = {"hello": "world"}
    log_to_file(value, filename=out, data_format="json", also_console=True)
    assert json.loads(out.read_text(encoding="utf-8")) == value
    captured = capsys.readouterr()
    assert '"hello": "world"' in captured.out


def test_log_to_file_raw_writes(tmp_path, capsys):
    out = tmp_path / "out.txt"
    log_to_file("hi", filename=out, data_format="raw", also_console=True)
    assert out.read_text(encoding="utf-8") == "hi"
    assert "hi" in capsys.readouterr().out


def test_log_to_file_raw_bytes_writes_binary(tmp_path, capsys):
    out = tmp_path / "cert.p12"
    payload = b"\x00\x01\x02"
    log_to_file(payload, filename=out, data_format="raw", also_console=True)
    assert out.read_bytes() == payload
    assert "<binary data: 3 bytes>" in capsys.readouterr().out


def test_log_to_file_csv_extracts_embedded_items(tmp_path, capsys):
    out = tmp_path / "out.csv"
    value = {"_embedded": {"items": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}}
    log_to_file(
        value,
        filename=out,
        data_format="csv",
        csv_fieldnames=["id", "name"],
        also_console=True,
    )
    text = out.read_text(encoding="utf-8")
    assert "id,name" in text.splitlines()[0]
    assert "1,a" in text
    assert "2,b" in text

    console = capsys.readouterr().out
    assert "id,name" in console
    assert "1,a" in console


def test_load_payload_file_json_dict(tmp_path):
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert load_payload_file(str(path)) == {"a": 1}


def test_load_payload_file_json_list_of_dicts(tmp_path):
    path = tmp_path / "payload.json"
    path.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
    assert load_payload_file(str(path)) == [{"a": 1}, {"a": 2}]


def test_load_payload_file_csv(tmp_path):
    path = tmp_path / "payload.csv"
    path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    rows = load_payload_file(str(path))
    assert rows == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]


def test_load_api_token_file_json(tmp_path):
    path = tmp_path / "token.json"
    path.write_text(json.dumps({"access_token": "abc123"}), encoding="utf-8")
    assert load_api_token_file(path) == "abc123"


def test_load_api_token_file_raw_string(tmp_path):
    path = tmp_path / "token.txt"
    path.write_text("abc123\n", encoding="utf-8")
    assert load_api_token_file(path) == "abc123"


def test_load_payload_file_rejects_unknown_ext(tmp_path):
    path = tmp_path / "payload.txt"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_payload_file(str(path))


def test_sanitize_secrets_masks_nested_fields():
    payload = {
        "client_secret": "top",
        "_embedded": {
            "items": [
                {"radius_secret": "abc123", "nested": {"tacacs_secret": "def456"}},
            ]
        },
    }

    sanitized = sanitize_secrets(payload, mask_secrets=True)

    assert sanitized["client_secret"] == ""
    assert sanitized["_embedded"]["items"][0]["radius_secret"] == ""
    assert sanitized["_embedded"]["items"][0]["nested"]["tacacs_secret"] == ""


def test_log_to_file_json_can_leave_secrets_visible(tmp_path):
    out = tmp_path / "out.json"
    value = {"radius_secret": "abc123"}
    log_to_file(value, filename=out, data_format="json", mask_secrets=False)
    assert json.loads(out.read_text(encoding="utf-8"))["radius_secret"] == "abc123"
