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

    # Extract data, frame ID (TI-130), source URI and source-file position to promote to extensions
    data = event.get('data', {})
    frame_id = None
    source_uri = None
    source_frame = None
    source_seconds = None
    if isinstance(data, dict):
        frame_id = data.get('id')
        # meta['src'] is the entry filter's source-file identity; may be
        # a real file URI (batch) or absent (streaming, or a filter that drops meta).
        # Promote only a non-empty string: it maps to a typed string column downstream, so
        # lists/dicts/None and blank/whitespace values must not leak through.
        meta = data.get('meta')
        if isinstance(meta, dict):
            src = meta.get('src')
            if isinstance(src, str) and src.strip():
                source_uri = src
            # src_frame / src_seconds are the frame's position within the source file (VideoIn
            # file sources): the 0-based frame index and the offset in seconds. They map to typed
            # numeric columns downstream. CloudEvents has no float attribute type, so both travel
            # as strings and the consumer parses them to INT64 / FLOAT64. bool is excluded because
            # it is an int subclass that would otherwise stringify as "True"/"False".
            src_frame = meta.get('src_frame')
            if isinstance(src_frame, int) and not isinstance(src_frame, bool):
                source_frame = str(src_frame)
            src_seconds = meta.get('src_seconds')
            if isinstance(src_seconds, (int, float)) and not isinstance(src_seconds, bool):
                source_seconds = repr(float(src_seconds))

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
        'data': data,
        # Required Plainsight extensions
        'pipelineid': pipeline_id,
        'filtername': event.get('filter_name'),
        'filtertopic': event.get('topic'),
    }

    # Add frame id as extension field if present (TI-130)
    if frame_id is not None:
        cloudevent['frameid'] = frame_id

    # Promote the source-file identity to a queryable extension so a downstream consumer
    # can store it as a typed column. Absent for streaming.
    if source_uri is not None:
        cloudevent['sourceuri'] = source_uri

    # Promote the frame's source-file position (index + seconds) as string extensions the
    # consumer parses into typed numeric columns. Absent for streaming/webcam and other sources
    # with no meaningful decoder position.
    if source_frame is not None:
        cloudevent['sourceframe'] = source_frame
    if source_seconds is not None:
        cloudevent['sourceseconds'] = source_seconds

    return cloudevent
