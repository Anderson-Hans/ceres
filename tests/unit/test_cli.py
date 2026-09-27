from ceres.cli import EXIT_NOT_ALLOWED, EXIT_OK, main


def test_phase_commands_are_not_run_before_acceptance(capsys):
    assert main(["data", "build", "--config", "configs/sources.yaml"]) == EXIT_NOT_ALLOWED
    assert main(["evaluate", "--phase", "1"]) == EXIT_NOT_ALLOWED
    assert main(["forecast", "--instrument", "ZCZ2026", "--as-of", "2026-09-27T23:00:00Z",
                 "--horizon", "21"]) == EXIT_NOT_ALLOWED
    assert "NOT_RUN" in capsys.readouterr().err


def test_preflight_commands_run():
    assert main(["spec", "verify"]) == EXIT_OK
    assert main(["experiment", "verify"]) == EXIT_OK
