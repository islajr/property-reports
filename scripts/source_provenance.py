"""Bind database observation freshness to an exact aggregate CSV export."""
from datetime import datetime
import hashlib
import json
from pathlib import Path


def metadata_path(csv_path):
    path = Path(csv_path)
    return path.with_name(path.name + '.meta.json')


def write_source_metadata(csv_path, exported_at, latest_observation):
    metadata = {'csv_sha256': hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
                'source_exported_at': exported_at.isoformat(),
                'latest_source_observation': latest_observation.isoformat() if latest_observation else None}
    metadata_path(csv_path).write_text(json.dumps(metadata, indent=2), encoding='utf-8')


def read_source_metadata(csv_path):
    path = metadata_path(csv_path)
    if not path.exists():
        return {}
    metadata = json.loads(path.read_text())
    if metadata['csv_sha256'] != hashlib.sha256(Path(csv_path).read_bytes()).hexdigest():
        raise ValueError('Source freshness metadata does not match this CSV export.')
    result = {}
    for key in ('source_exported_at', 'latest_source_observation'):
        value = metadata[key]
        if value is not None and datetime.fromisoformat(value).tzinfo is None:
            raise ValueError('Source timestamps must include a timezone.')
        result[key] = value
    return result


def format_timestamp(value):
    from datetime import timezone
    return datetime.fromisoformat(value).astimezone(timezone.utc).strftime('%d %B %Y, %H:%M UTC').lstrip('0')
