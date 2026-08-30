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


def test_a_member_inherits_the_scip_opt_in_from_the_root_that_claims_it(tmp_path):
    """The only way the overlay reaches a repository nobody here owns.

    A member is somebody else's checkout, so a `.graphrag.yaml` inside it is not
    on offer, and without inheritance `scip` can never be true for one. The
    workspace that federates 360 repositories turns the tier on from its own
    file or not at all.
    """
    from graphrag import registry

    root, member = tmp_path / "root", tmp_path / "member"
    root.mkdir()
    member.mkdir()
    (root / config.PROJECT_CONFIG_NAME).write_text(
        "exclude: [vendor]\nscip: true\nscip_indexers: [scip-go, scip-typescript]\n"
    )
    registry.claim(root, direct=True)
    registry.claim(member, root=root)

    got = projcfg.effective(member)
    assert got.scip is True
    assert got.scip_indexers == ["scip-go", "scip-typescript"]
    assert got.exclude == ["vendor"]


def test_a_member_with_its_own_config_inherits_no_scip_opt_in(tmp_path):
    """A config somebody wrote is obeyed whole. Nothing is merged into it."""
    from graphrag import registry

    root, member = tmp_path / "root2", tmp_path / "member2"
    root.mkdir()
    member.mkdir()
    (root / config.PROJECT_CONFIG_NAME).write_text("scip: true\nscip_indexers: [scip-go]\n")
    (member / config.PROJECT_CONFIG_NAME).write_text("languages: [go]\n")
    registry.claim(root, direct=True)
    registry.claim(member, root=root)

    got = projcfg.effective(member)
    assert got.scip is False
    assert got.scip_indexers == []


def test_an_unclaimed_project_inherits_nothing(tmp_path):
    """No root, no opt-in. The default stays off."""
    lone = tmp_path / "lone"
    lone.mkdir()
    assert projcfg.effective(lone).scip is False
