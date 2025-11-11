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

    def _extract_events(self, frames: dict[str, Frame]) -> list[dict]:
        """Extract events from frames based on topic filter"""
        events = []

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

            # Build event records
            events.append(
                {
                    'filter_name': source_filter_name,
                    'topic': source_topic,
                    'data': frame.data,
                }
            )

        if events:
            logger.debug(f"Extracted {len(events)} events from {len(frames)} frames")

        return events

    def _should_process_topic(self, topic: str) -> bool:
        """Check if topic should be processed"""
        topics = self.config.event_topics

        # Wildcard - process all except metrics
        if '*' in topics:
            return topic != '_metrics'

        # Explicit topic list
        return topic in topics


if __name__ == '__main__':
    FilterEventSink.run()
