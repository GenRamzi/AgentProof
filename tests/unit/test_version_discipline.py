import re
from pathlib import Path

from packaging.version import Version

from agentproof import __version__


def test_main_version_matches_pyproject_and_is_unpublished_devrelease():
    root = Path(__file__).parents[2]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    assert match is not None
    assert match.group(1) == __version__
    assert Version(__version__).is_devrelease
