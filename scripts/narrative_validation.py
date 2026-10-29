"""Validate commentary and bind it to the metrics used to write it."""

import hashlib
import json
import re
from report_evidence import evidence_for_market, numeric_tokens, takeaways

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
        fields = ("inventory_narrative", "pricing_narrative", "price_reduction_narrative") if narrative.get("_quality_version") == 2 else FIELDS
        for field in fields:
            if field in OPTIONAL_FIELDS and field in block and block[field] is None:
                continue
            if not isinstance(block.get(field), str) or not block[field].strip():
                raise ValueError(f"Invalid {market}.{field}: expected non-empty text.")
        takeaways = block.get("key_takeaways")
        if not isinstance(takeaways, list) or not takeaways or any(not isinstance(item, str) or not item.strip() for item in takeaways):
            raise ValueError(f"Invalid {market}.key_takeaways: expected a non-empty list of text.")
    if narrative.get("_quality_version") == 2:
        validate_editorial_quality(narrative, metrics)
    provenance = narrative.get("_provenance")
    if provenance is not None:
        if not isinstance(provenance, dict) or provenance.get("metrics_sha256") != metrics_digest(metrics):
            raise ValueError("Narrative metrics have changed. Regenerate with --force before rendering.")


def validate_editorial_quality(narrative, metrics):
    """Check evidence references and quantitative support, not all factual meaning."""
    limits = {'inventory_narrative': (80, 'inventory.'), 'pricing_narrative': (80, 'pricing.'),
              'price_reduction_narrative': (70, 'reductions.')}
    for market in ('sales', 'rentals'):
        data = metrics.get(market)
        if not data:
            continue
        block = narrative[market]
        facts = evidence_for_market(data, market)
        refs = block.get('evidence_refs')
        if not isinstance(refs, dict):
            raise ValueError(f'{market}: missing evidence references.')
        if block['key_takeaways'] != takeaways(data, market):
            raise ValueError(f'{market}: takeaways must match the computed facts.')
        sentences = set()
        for field, (limit, prefix) in limits.items():
            text = block[field]
            if len(text.split()) > limit:
                raise ValueError(f'{market}.{field}: exceeds {limit} words.')
            ids = refs.get(field)
            if not isinstance(ids, list) or not ids or any(not isinstance(key, str) or key not in facts or not key.startswith(prefix) for key in ids):
                raise ValueError(f'{market}.{field}: invalid or unrelated evidence reference.')
            allowed = numeric_tokens(' '.join(facts[key] for key in ids))
            if numeric_tokens(text) - allowed:
                raise ValueError(f'{market}.{field}: numeric claim is absent from the referenced evidence.')
            if re.search(r'\b(?:DOM|days on market|interest rates?|inflation|monetary policy)\b', text, re.I):
                raise ValueError(f'{market}.{field}: unsupported topic; keep to the supplied evidence.')
            for sentence in re.split(r'(?<=[.!?])\s+', text):
                normal = re.sub(r'\W+', ' ', sentence.casefold()).strip()
                if len(normal.split()) >= 6:
                    if normal in sentences:
                        raise ValueError(f'{market}: repeated commentary sentence.')
                    sentences.add(normal)
