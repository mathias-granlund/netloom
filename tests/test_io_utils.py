import json
import csv
import pytest

from arapy.io_utils import log_to_file, load_payload_file, _extract_by_path


def test_extract_by_path_happy():
    data = {"a": {"b": [{"c": 3}]}}
    assert _extract_by_path(data, ("a", "b", 0, "c")) == 3


def test_log_to_file_rejects_bad_mode(tmp_path):
    with pytest.raises(ValueError, match="mode must be"):
        log_to_file({"x": 1}, filename=tmp_path/"x.json", mode="x")


def test_log_to_file_rejects_bad_format(tmp_path):
    with pytest.raises(ValueError, match="data_format must be"):
        log_to_file({"x": 1}, filename=tmp_path/"x.bad", data_format="xml")


def test_log_to_file_json_writes_and_console(tmp_path, capsys):
    out = tmp_path/"out.json"
    value = {"hello": "world"}
    log_to_file(value, filename=out, data_format="json", also_console=True)
    assert json.loads(out.read_text(encoding="utf-8")) == value
    captured = capsys.readouterr()
    assert '"hello": "world"' in captured.out


def test_log_to_file_raw_writes(tmp_path, capsys):
    out = tmp_path/"out.txt"
    log_to_file("hi", filename=out, data_format="raw", also_console=True)
    assert out.read_text(encoding="utf-8") == "hi"
    assert "hi" in capsys.readouterr().out


def test_log_to_file_csv_extracts_embedded_items(tmp_path, capsys):
    out = tmp_path/"out.csv"
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

    # console output should include header and at least one row
    c = capsys.readouterr().out
    assert "id,name" in c
    assert "1,a" in c


def test_load_payload_file_json_dict(tmp_path):
    p = tmp_path/"payload.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert load_payload_file(str(p)) == {"a": 1}


def test_load_payload_file_json_list_of_dicts(tmp_path):
    p = tmp_path/"payload.json"
    p.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
    assert load_payload_file(str(p)) == [{"a": 1}, {"a": 2}]


def test_load_payload_file_csv(tmp_path):
    p = tmp_path/"payload.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    rows = load_payload_file(str(p))
    assert rows == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]


def test_load_payload_file_rejects_unknown_ext(tmp_path):
    p = tmp_path/"payload.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_payload_file(str(p))
