"""Tests for the CLI."""

from two_brain_audit.cli import main


class TestCLI:
    def test_no_args_returns_zero(self):
        assert main([]) == 0

    def test_help_flag(self):
        try:
            main(["--help"])
        except SystemExit as e:
            assert e.code == 0

    def test_init_creates_files(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        result = main(["init", "--db", db, "--baseline", baseline])
        assert result == 0
        assert (tmp_path / "test.db").exists()
        assert (tmp_path / "test_baseline.json").exists()

    def test_status_empty(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        main(["init", "--db", db, "--baseline", baseline])
        result = main(["status", "--db", db, "--baseline", baseline])
        assert result == 0

    def test_health_empty(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        main(["init", "--db", db, "--baseline", baseline])
        result = main(["health", "--db", db, "--baseline", baseline])
        # ok=True when no scores (no failing dimensions)
        assert result == 0

    def test_export_json(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        out = str(tmp_path / "report.json")
        main(["init", "--db", db, "--baseline", baseline])
        result = main(["export", "json", "-o", out, "--db", db, "--baseline", baseline])
        assert result == 0
        assert (tmp_path / "report.json").exists()

    def test_register_preset(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        main(["init", "--db", db, "--baseline", baseline])
        result = main(["register", "--preset", "python", "--db", db, "--baseline", baseline])
        assert result == 0

    def test_run_with_target(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        target = str(tmp_path)
        # Create a minimal .two-brain-audit.json so auto-load works
        import json
        (tmp_path / ".two-brain-audit.json").write_text(
            json.dumps({"preset": "python", "created": True}), encoding="utf-8"
        )
        main(["init", "--db", db, "--baseline", baseline])
        result = main(["run", "light", "--db", db, "--baseline", baseline, "--target", target])
        assert result == 0

    def test_register_persists_config(self, tmp_path):
        import json
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        main(["init", "--db", db, "--baseline", baseline])
        main(["register", "--preset", "python", "--db", db, "--baseline", baseline, "--target", str(tmp_path)])
        config = json.loads((tmp_path / ".two-brain-audit.json").read_text())
        assert config["preset"] == "python"

    def test_run_no_dimensions(self, tmp_path):
        db = str(tmp_path / "test.db")
        baseline = str(tmp_path / "test_baseline.json")
        main(["init", "--db", db, "--baseline", baseline])
        result = main(["run", "light", "--db", db, "--baseline", baseline])
        assert result == 1  # no dimensions = error
