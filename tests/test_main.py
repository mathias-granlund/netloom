import arapy.main as main


def test_parse_cli_basic():
    argv = ["arapy", "identities", "endpoint", "list", "--limit=10", "--console", "--log_level=debug"]
    args = main.parse_cli(argv)
    assert args["module"] == "identities"
    assert args["service"] == "endpoint"
    assert args["action"] == "list"
    assert args["limit"] == "10"
    assert args["console"] is True
    assert args["log_level"] == "debug"


def test_parse_cli_ignores_unknown_flags_in_completion_mode():
    argv = ["arapy", "--_complete", "--_cur=ep", "-x", "identities"]
    args = main.parse_cli(argv)
    assert args["_complete"] is True


def test_complete_outputs_modules(capsys):
    main._complete(["--_cur="])
    out = capsys.readouterr().out.strip().splitlines()
    assert "identities" in out  # from commands.DISPATCH


def test_complete_outputs_services_for_module(capsys):
    main._complete(["identities", "--_cur="])
    out = capsys.readouterr().out.strip().splitlines()
    assert "endpoint" in out


def test_complete_outputs_actions_for_service(capsys):
    main._complete(["identities", "endpoint", "--_cur="])
    out = capsys.readouterr().out.strip().splitlines()
    assert "list" in out
    assert "get" in out
