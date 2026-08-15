from __future__ import annotations

import json
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib

from datetime import datetime, timezone
from pathlib import Path


def normalized_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    packages = [
        {
            "SPDXID": "SPDXRef-Package-AgentProof",
            "name": project["name"],
            "versionInfo": project["version"],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
        }
    ]
    for index, requirement in enumerate(project.get("dependencies", []), start=1):
        packages.append(
            {
                "SPDXID": f"SPDXRef-Package-Dependency-{index}",
                "name": normalized_name(requirement),
                "versionInfo": requirement,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
            }
        )
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{project['name']}-{project['version']}",
        "documentNamespace": f"https://github.com/GenRamzi/AgentProof/sbom/{project['version']}",
        "creationInfo": {
            "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "creators": ["Tool: AgentProof SBOM generator"],
        },
        "packages": packages,
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "dist" / "SBOM.spdx.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
