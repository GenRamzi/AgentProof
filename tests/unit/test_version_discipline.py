from pathlib import Path

import tomllib
from packaging.version import Version

from agentproof import __version__


def test_main_version_matches_pyproject_and_is_unpublished_devrelease():
    root = Path(__file__).parents[2]
    with (root / "pyproject.toml").open("rb") as handle:
        package_version = tomllib.load(handle)["project"]["version"]
    assert package_version == __version__
    assert Version(__version__).is_devrelease
