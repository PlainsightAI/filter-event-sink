"""
Background thread for event batching and HTTP posting
"""

import gzip
import json
import logging
import queue
import time
from queue import Queue
from threading import Event, Thread

import requests

from .cloudevents import build_cloudevent
from .config import FilterEventSinkConfig

logger = logging.getLogger(__name__)


class EventSinkThread(Thread):
    """
    Background thread that accumulates events and POSTs them to API endpoint

    Implements batch flushing based on:
    - Size limit (max_batch_size_bytes)
    - Count limit (max_batch_events)
    - Time limit (flush_interval_seconds)
    """

    def __init__(
        self, event_queue: Queue, config: FilterEventSinkConfig, stop_evt: Event
    ):
        super().__init__(daemon=True, name='EventSinkThread')
        self.event_queue = event_queue
        self.config = config
        self.stop_evt = stop_evt

        # Batch state
        self.batch_buffer: list[dict] = []
        self.batch_size_bytes = 0
        self.last_flush_time = time.time()

        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Authorization': f'Bearer {self.config.api_token}',
                'Content-Type': 'application/cloudevents-batch+json',
            }
        )

        # Add custom headers if provided
        if self.config.api_custom_headers:
            self.session.headers.update(self.config.api_custom_headers)
            logger.info(
                f"Added custom headers: {list(self.config.api_custom_headers.keys())}"
            )

        # API endpoint URL
        self.api_url = self.config.api_endpoint

        # Get pipeline_id from config
        self.pipeline_id = self.config.pipeline_id

        logger.info(
            f"EventSinkThread initialized: endpoint={self.api_url}, "
            f"pipeline_id={self.pipeline_id}, "
            f"max_batch_events={self.config.max_batch_events}, "
            f"flush_interval={self.config.flush_interval_seconds}s"
        )

    def stop(self) -> None:
        """Stop the thread and wait for graceful shutdown"""
        logger.info("Stopping EventSinkThread...")
        self.stop_evt.set()
        self.join(timeout=30)
        if self.is_alive():
            logger.warning("EventSinkThread did not stop gracefully within timeout")
        else:
            logger.info("EventSinkThread stopped successfully")

    def run(self) -> None:
        """Main thread loop: accumulate events and flush batches"""
        logger.info("EventSinkThread started")

        try:
            while not self.stop_evt.is_set():
                try:
                    # Get event with timeout to check stop_evt periodically
                    event = self.event_queue.get(timeout=1.0)
                    self._add_event_to_batch(event)

                    # Check if we should flush
                    if self._should_flush():
                        self._flush_batch()

                except queue.Empty:
                    # Timeout - check if we should flush based on time
                    if self._should_flush():
                        self._flush_batch()

        except Exception as e:
            logger.error(f"Unexpected error in EventSinkThread: {e}", exc_info=True)

        finally:
            # Final flush on shutdown
            if self.batch_buffer:
                logger.info(
                    f"Flushing {len(self.batch_buffer)} remaining events on shutdown"
                )
                self._flush_batch()

            # Clean up session
            self.session.close()
            logger.info("EventSinkThread cleanup completed")

    def _add_event_to_batch(self, event: dict) -> None:
        """Add event to batch buffer and update size"""
        cloudevent = build_cloudevent(
            event=event,
            pipeline_id=self.pipeline_id,
            event_source_base=self.config.event_source_base,
        )
        event_json = json.dumps(cloudevent)
        event_size = len(event_json.encode('utf-8'))

        self.batch_buffer.append(cloudevent)
        self.batch_size_bytes += event_size

    def _should_flush(self) -> bool:
        """Check if batch should be flushed"""
        if not self.batch_buffer:
            return False

        # Check size limit
        if self.batch_size_bytes >= self.config.max_batch_size_bytes:
            logger.debug(
                f"Flushing batch: size limit reached ({self.batch_size_bytes} bytes)"
            )
            return True

        # Check count limit
        if len(self.batch_buffer) >= self.config.max_batch_events:
            logger.debug(
                f"Flushing batch: count limit reached ({len(self.batch_buffer)} events)"
            )
            return True

        # Check time limit
        time_since_last_flush = time.time() - self.last_flush_time
        if time_since_last_flush >= self.config.flush_interval_seconds:
            logger.debug(
                f"Flushing batch: time limit reached "
                f"({time_since_last_flush:.1f}s >= {self.config.flush_interval_seconds}s)"
            )
            return True

        return False

    def _flush_batch(self) -> bool:
        """Flush current batch to API endpoint"""
        if not self.batch_buffer:
            return True

        batch_count = len(self.batch_buffer)
        batch_size = self.batch_size_bytes

        logger.info(f"Flushing batch: {batch_count} events, {batch_size} bytes")

        success = self._post_batch(self.batch_buffer)

        if success:
            logger.info(f"Successfully posted {batch_count} events to API")
        else:
            logger.error(f"Failed to post {batch_count} events after retries")

        # Clear batch regardless of success (no DLQ, just log errors)
        self.batch_buffer = []
        self.batch_size_bytes = 0
        self.last_flush_time = time.time()

        return success

    def _post_batch(self, batch: list[dict]) -> bool:
        """POST batch to API with retry logic"""
        # Serialize to JSON
        payload = json.dumps(batch).encode('utf-8')
        original_size = len(payload)

        # Compress if enabled
        headers = {}
        if self.config.enable_gzip:
            payload = gzip.compress(
                payload, compresslevel=self.config.gzip_compression_level
            )
            headers['Content-Encoding'] = 'gzip'
            logger.debug(
                f"Compressed batch: {original_size} -> {len(payload)} bytes "
                f"({100 * len(payload) / original_size:.1f}%)"
            )

        # Retry loop
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    self.api_url,
                    data=payload,
                    headers=headers,
                    timeout=self.config.request_timeout_seconds,
                )

                if response.status_code == 202:
                    # Success
                    return True

                elif response.status_code >= 500:
                    # Server error - retry
                    logger.warning(
                        f"Server error {response.status_code} on attempt {attempt + 1}/{self.config.max_retries}: "
                        f"{response.text[:200]}"
                    )
                    if attempt < self.config.max_retries - 1:
                        sleep_time = self.config.retry_backoff_base**attempt
                        logger.info(f"Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue

                else:
                    # Client error - don't retry
                    logger.error(
                        f"Client error {response.status_code}, not retrying: {response.text[:500]}"
                    )
                    return False

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Request failed on attempt {attempt + 1}/{self.config.max_retries}: {e}"
                )
                if attempt < self.config.max_retries - 1:
                    sleep_time = self.config.retry_backoff_base**attempt
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue

        # All retries exhausted
        logger.error(f"Failed to post batch after {self.config.max_retries} attempts")
        return False
