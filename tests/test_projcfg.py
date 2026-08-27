"""Strict project config. Every rejection names the file and the key."""

from __future__ import annotations

import pytest

from graphrag import config, projcfg


def test_no_config_is_the_defaults(tmp_path):
    assert projcfg.load(tmp_path) == projcfg.ProjectConfig()


def test_an_unknown_key_is_an_error_that_names_the_closest_one(tmp_path):
    (tmp_path / config.PROJECT_CONFIG_NAME).write_text("excludes:\n  - build\n")
    with pytest.raises(projcfg.ConfigError) as caught:
        projcfg.load(tmp_path)
    message = str(caught.value)
    assert "unknown key 'excludes'" in message
    assert "did you mean 'exclude'" in message


def test_the_retired_filename_is_refused_and_not_ignored(tmp_path):
    (tmp_path / config.RETIRED_CONFIG_NAME).write_text("enabled = false\n")
    with pytest.raises(projcfg.ConfigError, match="retired config name"):
        projcfg.load(tmp_path)


def test_a_wrong_type_is_rejected_before_it_reaches_the_indexer(tmp_path):
    (tmp_path / config.PROJECT_CONFIG_NAME).write_text("exclude: build\n")
    with pytest.raises(projcfg.ConfigError, match="must be a list of strings"):
        projcfg.load(tmp_path)

    (tmp_path / config.PROJECT_CONFIG_NAME).write_text("scip: yes-please\n")
    with pytest.raises(projcfg.ConfigError, match="must be true or false"):
        projcfg.load(tmp_path)


def test_a_valid_config_round_trips_every_field(tmp_path):
    (tmp_path / config.PROJECT_CONFIG_NAME).write_text(
        "enabled: true\nexclude: [fixtures]\nlanguages: [python]\n"
        "members: [../other]\nscip: true\nscip_indexers: [scip-python]\n"
    )
    parsed = projcfg.load(tmp_path)
    assert parsed.exclude == ["fixtures"]
    assert parsed.languages == ["python"]
    assert parsed.members == ["../other"]
    assert parsed.scip is True
    assert parsed.scip_indexers == ["scip-python"]


def test_an_empty_document_is_not_an_error(tmp_path):
    (tmp_path / config.PROJECT_CONFIG_NAME).write_text("# nothing yet\n")
    assert projcfg.load(tmp_path) == projcfg.ProjectConfig()
