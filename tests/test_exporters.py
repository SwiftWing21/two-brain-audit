"""Tests for JSON, CSV, and Markdown exporters."""

import json

import pytest

from scorerift import AuditEngine, Dimension, Tier
from scorerift.exporters import export_csv, export_json, export_markdown


@pytest.fixture
def engine(tmp_path):
    e = AuditEngine(
        db_path=str(tmp_path / "test.db"),
        baseline_path=str(tmp_path / "baseline.json"),
    )
    e.register(Dimension(name="test_dim", check=lambda: (0.9, {"ok": True}), tier=Tier.LIGHT))
    e.run_tier("light")
    return e


class TestJsonExporter:
    def test_returns_valid_json(self, engine):
        output = export_json(engine)
        data = json.loads(output)
        assert "health" in data
        assert "dimensions" in data
        assert len(data["dimensions"]) == 1

    def test_writes_to_file(self, engine, tmp_path):
        path = tmp_path / "report.json"
        export_json(engine, path=str(path))
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["health"]["grade"]


class TestCsvExporter:
    def test_has_header_row(self, engine):
        output = export_csv(engine)
        lines = output.strip().splitlines()
        assert len(lines) == 2  # header + 1 row
        assert "dimension" in lines[0]
        assert "test_dim" in lines[1]

    def test_writes_to_file(self, engine, tmp_path):
        path = tmp_path / "report.csv"
        export_csv(engine, path=str(path))
        assert path.exists()


class TestMarkdownExporter:
    def test_has_table(self, engine):
        output = export_markdown(engine)
        assert "| Dimension |" in output
        assert "test_dim" in output
        assert "scorerift" in output

    def test_writes_to_file(self, engine, tmp_path):
        path = tmp_path / "report.md"
        export_markdown(engine, path=str(path))
        assert path.exists()
