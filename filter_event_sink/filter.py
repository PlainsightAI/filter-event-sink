"""
Event Sink Filter - Collects events from filter pipeline and posts to CloudEvents API

This filter implements a dual-thread architecture:
- Main thread: Extract and enqueues events
- Background thread: Batches events and POSTs to API endpoint
"""

import logging
import queue
from queue import Queue
from typing import Optional

from openfilter.filter_runtime.filter import Filter, Frame

from .config import FilterEventSinkConfig
from .thread import EventSinkThread

__all__ = ['FilterEventSinkConfig', 'FilterEventSink']

logger = logging.getLogger(__name__)


class FilterEventSink(Filter):
    """
    Event Sink Filter - Collects events from filter pipeline and posts to CloudEvents API

    This filter:
    - Extracts events from frame.data based on topic filter
    - Extracts frame ID from _filter hidden topic (TI-130)
    - Batches events and POSTs to CloudEvents API endpoint
    - Runs background thread for async HTTP posting
    """

    FILTER_TYPE = 'Output'

    @classmethod
    def normalize_config(cls, config: FilterEventSinkConfig) -> FilterEventSinkConfig:
        """Normalize and validate configuration"""
        config = FilterEventSinkConfig(super().normalize_config(config))
        return FilterEventSinkConfig.normalize(config)

    def setup(self, config: FilterEventSinkConfig) -> None:
        """Initialize and start background event sink thread"""
        logger.info(
            f"Setting up Event Sink filter: pipeline_id={self.config.pipeline_id}, "
            f"endpoint={config.api_endpoint}"
        )

        self.event_queue: Optional[Queue] = None
        self.event_sink_thread: Optional[EventSinkThread] = None

        # Create event queue
        self.event_queue = Queue(maxsize=config.event_queue_size)

        # Create and start background thread
        self.event_sink_thread = EventSinkThread(
            event_queue=self.event_queue,
            config=config,
            stop_evt=self.stop_evt,  # Share stop event from Filter base class
        )
        self.event_sink_thread.start()

        logger.info("Event Sink filter setup completed")

    def shutdown(self) -> None:
        """Stop background thread and flush remaining events"""
        logger.info("Shutting down Event Sink filter...")

        if self.event_sink_thread:
            self.event_sink_thread.stop()

        logger.info("Event Sink filter shutdown completed")

    def process(self, frames: dict[str, Frame]):
        """Process frames: extract events and queue for background posting"""
        # Extract events from frames
        events = self._extract_events(frames)

        # Queue events for background thread
        for event in events:
            try:
                self.event_queue.put_nowait(event)
            except queue.Full:
                logger.error(
                    "Event queue full, dropping event "
                    "(increase event_queue_size or reduce event rate)"
                )

    def _extract_filter_metadata(self, frames: dict[str, Frame]) -> dict:
        """Extract metadata from _filter hidden topic (TI-130)

        The _filter topic is emitted by openfilter runtime and contains:
        - id: Frame ID(s) from input frames' meta.id or auto-generated

        Returns dict with filter metadata, or empty dict if _filter not present.
        """
        filter_metadata = {}

        # Check for _filter topic (format: SourceName___filter or _filter)
        for topic, frame in frames.items():
            # Match _filter hidden topic:
            # - Standalone: '_filter'
            # - With source prefix: 'SourceName___filter' (SourceName + __ + _filter)
            if topic == '_filter' or topic.endswith('___filter'):
                if frame and frame.data and isinstance(frame.data, dict):
                    frame_id = frame.data.get('id')
                    if frame_id is not None:
                        filter_metadata['id'] = frame_id
                        logger.debug(f"Extracted frame id from {topic}: {frame_id}")
                    # Preserve any other fields from _filter (skip None values)
                    for key, value in frame.data.items():
                        if key not in filter_metadata and value is not None:
                            filter_metadata[key] = value
                break  # Only use first _filter topic found

        return filter_metadata

    def _merge_event_data(self, frame_data: dict, filter_metadata: dict) -> dict:
        """Merge frame data with filter metadata, handling key collisions

        Strategy for collision handling:
        1. frame_data keys take precedence (they are the actual event payload)
        2. Colliding keys from filter_metadata are preserved with 'filter_' prefix
        3. Non-colliding keys from filter_metadata are added directly
        """
        if not filter_metadata:
            return frame_data

        if not isinstance(frame_data, dict):
            return {'data': frame_data, **filter_metadata}

        merged = dict(frame_data)
        for key, value in filter_metadata.items():
            if key in merged:
                prefixed_key = f'filter_{key}'
                if prefixed_key not in merged:
                    merged[prefixed_key] = value
                    logger.debug(f"Key collision for '{key}': preserved as '{prefixed_key}'")
            else:
                merged[key] = value

        return merged

    def _extract_events(self, frames: dict[str, Frame]) -> list[dict]:
        """Extract events from frames based on topic filter"""
        events = []

        # Extract filter metadata (frame ID) from _filter topic (TI-130)
        filter_metadata = self._extract_filter_metadata(frames)

        for topic, frame in frames.items():
            # Skip if topic not in filter list
            if not self._should_process_topic(topic):
                continue

            # Skip if no data
            if not frame.data:
                continue

            topic_parts = topic.split('__')
            source_filter_name = topic_parts[0]
            source_topic = 'main'

            if len(topic_parts) > 1:
                source_topic = topic_parts[1]

            # Merge frame data with filter metadata (TI-130)
            merged_data = self._merge_event_data(frame.data, filter_metadata)

            # Build event records
            events.append(
                {
                    'filter_name': source_filter_name,
                    'topic': source_topic,
                    'data': merged_data,
                }
            )

        if events:
            logger.debug(f"Extracted {len(events)} events from {len(frames)} frames")

        return events

    def _should_process_topic(self, topic: str) -> bool:
        """Check if topic should be processed

        Hidden topics (starting with '_') are never processed as events.
        They contain metadata like _filter (frame IDs) and _metrics.
        """
        # Extract the actual topic name (after source prefix if present)
        topic_parts = topic.split('__')
        extracted_topic = topic_parts[-1] if len(topic_parts) > 1 else topic

        # Skip hidden topics (start with '_')
        if topic.startswith('_') or extracted_topic.startswith('_'):
            return False

        topics = self.config.event_topics

        # Wildcard - process all non-hidden topics
        if '*' in topics:
            return True

        # Explicit topic list
        return topic in topics


if __name__ == '__main__':
    FilterEventSink.run()
