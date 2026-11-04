from radar import __main__ as cli


def test_reads_the_file_the_cli_documents(tmp_path, monkeypatch):
    monkeypatch.delenv("NTR_TEST_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text('# a comment\nNTR_TEST_KEY="abc"\n\nOTHER_TEST=x\n')
    cli.load_env(env)
    import os
    assert os.environ["NTR_TEST_KEY"] == "abc"
    assert os.environ["OTHER_TEST"] == "x"


def test_the_shell_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("NTR_TEST_KEY", "shell")
    env = tmp_path / ".env"
    env.write_text("NTR_TEST_KEY=file\n")
    cli.load_env(env)
    import os
    assert os.environ["NTR_TEST_KEY"] == "shell"


def test_no_file_is_not_an_error(tmp_path):
    cli.load_env(tmp_path / "missing.env")
