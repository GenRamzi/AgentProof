from __future__ import annotations

import json
from typing import Any


def render_json(receipt: Any) -> str:
    data = receipt.to_dict() if hasattr(receipt, "to_dict") else receipt
    return json.dumps(data, indent=2, ensure_ascii=False)
