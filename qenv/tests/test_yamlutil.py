from __future__ import annotations

from pathlib import Path

from yamlutil import load_yaml_mapping


def test_load_yaml_mapping_fallback_parses_empty_inline_list(tmp_path: Path) -> None:
    config_path = tmp_path / "package.yaml"
    config_path.write_text(
        """version: 1

requires:
  tools:
    required: []
""",
        encoding="utf-8",
    )

    mapping = load_yaml_mapping(config_path, error_type=RuntimeError)

    assert mapping["requires"]["tools"]["required"] == []