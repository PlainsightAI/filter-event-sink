"""
CloudEvent building utilities
"""

import uuid
from datetime import datetime, timezone
from typing import Any


def build_cloudevent(
    event: dict[str, Any], pipeline_id: str, event_source_base: str
) -> dict[str, Any]:
    """
    Build CloudEvent v1.0 compliant event

    Args:
        event: Extracted event data with keys: filter_name, topic, data
        pipeline_id: Pipeline instance ID (e.g., "run-20251027-abc123")
        event_source_base: CloudEvent source prefix (e.g., "filter://")

    Returns:
        CloudEvent v1.0 compliant dictionary
    """
    # Generate unique ID
    event_id = str(uuid.uuid4())

    # Determine event type
    event_type = 'com.plainsight.event.generic'

    # Build source (use pipeline_id as the instance identifier)
    source = f"{event_source_base}{pipeline_id}/{event.get('filter_name')}/{event.get('topic')}"

    # Get timestamp
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # Build CloudEvent
    cloudevent = {
        # Required CloudEvents v1.0 fields
        'id': event_id,
        'type': event_type,
        'source': source,
        'specversion': '1.0',
        'time': timestamp,
        # Optional CloudEvents fields
        'datacontenttype': 'application/json',
        'data': event.get('data', {}),
        # Required Plainsight extensions
        'pipelineid': pipeline_id,
        'filtername': event.get('filter_name'),
        'filtertopic': event.get('topic'),
    }

    return cloudevent
