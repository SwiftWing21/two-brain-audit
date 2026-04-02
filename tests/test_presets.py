"""Tests for preset dimension configurations."""

from two_brain_audit import Dimension
from two_brain_audit.presets import PRESETS


class TestPresetsStructure:
    def test_all_presets_exist(self):
        expected = {"python", "api", "database", "infrastructure", "ml_pipeline"}
        assert set(PRESETS.keys()) == expected

    def test_all_presets_return_dimension_lists(self):
        for name, dims in PRESETS.items():
            assert isinstance(dims, list), f"{name} is not a list"
            for d in dims:
                assert isinstance(d, Dimension), f"{name} contains non-Dimension: {type(d)}"

    def test_python_has_8_dimensions(self):
        assert len(PRESETS["python"]) == 8

    def test_dimension_names_unique_per_preset(self):
        for preset_name, dims in PRESETS.items():
            names = [d.name for d in dims]
            assert len(names) == len(set(names)), f"Duplicate names in {preset_name}"

    def test_all_dimensions_have_check(self):
        for preset_name, dims in PRESETS.items():
            for d in dims:
                assert callable(d.check), f"{preset_name}.{d.name} check is not callable"

    def test_all_dimensions_have_tier(self):
        from two_brain_audit.tiers import Tier
        for preset_name, dims in PRESETS.items():
            for d in dims:
                assert isinstance(d.tier, Tier), f"{preset_name}.{d.name} tier is not Tier"

    def test_confidence_in_range(self):
        for preset_name, dims in PRESETS.items():
            for d in dims:
                assert 0.0 <= d.confidence <= 1.0, f"{preset_name}.{d.name} confidence out of range"
