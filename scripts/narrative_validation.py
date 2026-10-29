"""Validate commentary and bind it to the metrics used to write it."""

import hashlib
import json

FIELDS = (
    "executive_summary", "inventory_narrative", "pricing_narrative",
    "lagos_narrative", "abuja_narrative", "other_cities_narrative",
    "price_reduction_narrative", "outlook",
)
OPTIONAL_FIELDS = {"abuja_narrative", "other_cities_narrative"}


def metrics_digest(metrics: dict) -> str:
    encoded = json.dumps(metrics, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_narrative(narrative: dict, metrics: dict) -> None:
    if not isinstance(narrative, dict):
        raise ValueError("Narrative must be a JSON object.")
    for market in ("sales", "rentals"):
        block = narrative.get(market)
        if not metrics.get(market):
            if block is not None:
                raise ValueError(f"Unexpected {market} narrative without metrics.")
            continue
        if not isinstance(block, dict):
            raise ValueError(f"Missing {market} narrative object.")
        for field in FIELDS:
            if field in OPTIONAL_FIELDS and field in block and block[field] is None:
                continue
            if not isinstance(block.get(field), str) or not block[field].strip():
                raise ValueError(f"Invalid {market}.{field}: expected non-empty text.")
        takeaways = block.get("key_takeaways")
        if not isinstance(takeaways, list) or not takeaways or any(not isinstance(item, str) or not item.strip() for item in takeaways):
            raise ValueError(f"Invalid {market}.key_takeaways: expected a non-empty list of text.")
    provenance = narrative.get("_provenance")
    if provenance is not None:
        if not isinstance(provenance, dict) or provenance.get("metrics_sha256") != metrics_digest(metrics):
            raise ValueError("Narrative metrics have changed. Regenerate with --force before rendering.")
