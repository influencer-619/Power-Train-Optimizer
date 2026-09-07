"""Canonical configuration fingerprint for result↔input integrity."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from config.defaults import MODEL_VERSION


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        # Parameter wrapper: keep value + source if present
        if "value" in obj and ("source" in obj or "unit" in obj or "kind" in obj):
            return {
                "value": obj.get("value"),
                "source": obj.get("source"),
            }
        return {k: _normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    if isinstance(obj, float):
        return round(obj, 12)
    return obj


def config_fingerprint(config: dict, extra: dict | None = None) -> str:
    """Stable SHA-256 hex digest of simulation-relevant config (+ optional extras)."""
    payload = {
        "model_version": MODEL_VERSION,
        "config": _normalize(deepcopy(config)),
    }
    if extra:
        payload["extra"] = _normalize(deepcopy(extra))
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
