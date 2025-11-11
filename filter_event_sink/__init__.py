"""
Event Sink Filter - CloudEvents API ingestion bridge

This package provides an OpenFilter component that collects events from filter
pipelines and reliably delivers them to the Plainsight API's CloudEvents
ingestion compatible endpoint.

Main components:
- FilterEventSink: Main filter class (event collection)
- FilterEventSinkConfig: Configuration class
- EventSinkThread: Background thread for batching and HTTP POSTing
- build_cloudevent: CloudEvent v1.0 builder utility
"""

from .cloudevents import build_cloudevent
from .config import FilterEventSinkConfig
from .filter import FilterEventSink
from .thread import EventSinkThread

__all__ = [
    'FilterEventSink',
    'FilterEventSinkConfig',
    'EventSinkThread',
    'build_cloudevent',
]

__version__ = '1.0.0'
