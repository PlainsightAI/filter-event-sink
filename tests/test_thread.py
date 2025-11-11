#!/usr/bin/env python

"""
Unit tests for EventSinkThread

Tests batch accumulation, HTTP posting, retry logic, and thread lifecycle
"""

import gzip
import json
import time
import unittest
from queue import Queue
from threading import Event

import responses

from filter_event_sink import EventSinkThread, FilterEventSink, FilterEventSinkConfig


class TestBatchAccumulation(unittest.TestCase):
    """Test batch accumulation and flush conditions"""

    def setUp(self):
        """Set up test thread"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            max_batch_size_bytes=1000,  # Small for testing
            max_batch_events=5,
            flush_interval_seconds=1.0,
        )
        self.config = FilterEventSink.normalize_config(config)
        self.thread = EventSinkThread(
            event_queue=Queue(), config=self.config, stop_evt=Event()
        )

    def test_should_flush_size_limit(self):
        """Test flush on size limit"""
        # Add events until size limit reached
        for i in range(10):
            event = {'topic': 'main', 'data': {'index': i, 'large_data': 'x' * 100}}
            self.thread._add_event_to_batch(event)

        self.assertTrue(self.thread._should_flush())

    def test_should_flush_count_limit(self):
        """Test flush on count limit"""
        # Add exactly max_batch_events
        for i in range(self.config.max_batch_events):
            event = {'topic': 'main', 'data': {'index': i}}
            self.thread._add_event_to_batch(event)

        self.assertTrue(self.thread._should_flush())

    def test_should_flush_time_limit(self):
        """Test flush on time limit"""
        # Add one event
        event = {'topic': 'main', 'data': {'test': 'data'}}
        self.thread._add_event_to_batch(event)

        # Should not flush immediately
        self.assertFalse(self.thread._should_flush())

        # Wait for time limit
        time.sleep(1.1)

        # Should flush now
        self.assertTrue(self.thread._should_flush())

    def test_should_not_flush_empty_batch(self):
        """Test that empty batch doesn't trigger flush"""
        self.assertFalse(self.thread._should_flush())


class TestHTTPPosting(unittest.TestCase):
    """Test HTTP posting with retry logic"""

    def setUp(self):
        """Set up test thread"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com/filter-pipelines/test/events',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            max_retries=3,
            retry_backoff_base=0.1,  # Fast retries for testing
        )
        self.config = FilterEventSink.normalize_config(config)
        self.thread = EventSinkThread(
            event_queue=Queue(), config=self.config, stop_evt=Event()
        )

    @responses.activate
    def test_successful_post(self):
        """Test successful HTTP POST"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        result = self.thread._post_batch(batch)

        self.assertTrue(result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_retry_on_server_error(self):
        """Test retry on 500 error"""
        # First two attempts fail, third succeeds
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=500,
        )
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=500,
        )
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        result = self.thread._post_batch(batch)

        self.assertTrue(result)
        self.assertEqual(len(responses.calls), 3)

    @responses.activate
    def test_no_retry_on_client_error(self):
        """Test no retry on 400 error"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=400,
            json={'error': 'Bad request'},
        )

        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        result = self.thread._post_batch(batch)

        self.assertFalse(result)
        self.assertEqual(len(responses.calls), 1)  # No retry

    @responses.activate
    def test_retry_exhaustion(self):
        """Test all retries exhausted"""
        # All attempts fail
        for _ in range(3):
            responses.add(
                responses.POST,
                'https://api.example.com/filter-pipelines/test/events',
                status=500,
            )

        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        result = self.thread._post_batch(batch)

        self.assertFalse(result)
        self.assertEqual(len(responses.calls), 3)

    @responses.activate
    def test_gzip_compression(self):
        """Test that payload is gzipped when enabled"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        self.config.enable_gzip = True
        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        self.thread._post_batch(batch)

        # Check that Content-Encoding header was set
        request = responses.calls[0].request
        self.assertEqual(request.headers.get('Content-Encoding'), 'gzip')

        # Check that body is gzipped
        decompressed = gzip.decompress(request.body)
        data = json.loads(decompressed)
        self.assertEqual(len(data), 1)

    @responses.activate
    def test_no_compression_when_disabled(self):
        """Test that payload is not gzipped when disabled"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        self.config.enable_gzip = False
        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        self.thread._post_batch(batch)

        # Check that Content-Encoding header was not set
        request = responses.calls[0].request
        self.assertNotIn('Content-Encoding', request.headers)

        # Check that body is plain JSON
        data = json.loads(request.body)
        self.assertEqual(len(data), 1)

    @responses.activate
    def test_custom_headers_sent(self):
        """Test that custom headers are sent in HTTP requests"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        # Create config with custom headers
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com/filter-pipelines/test/events',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            api_custom_headers={
                'X-Scope-OrgID': '48eec17d-3089-4d13-a107-24f5f4cf84c7',
                'X-Custom-Header': 'custom-value',
            },
        )
        config = FilterEventSink.normalize_config(config)

        thread = EventSinkThread(event_queue=Queue(), config=config, stop_evt=Event())

        batch = [{'id': '1', 'type': 'test', 'source': 'test', 'specversion': '1.0'}]
        result = thread._post_batch(batch)

        self.assertTrue(result)
        self.assertEqual(len(responses.calls), 1)

        # Verify custom headers were sent
        request = responses.calls[0].request
        self.assertEqual(
            request.headers['X-Scope-OrgID'], '48eec17d-3089-4d13-a107-24f5f4cf84c7'
        )
        self.assertEqual(request.headers['X-Custom-Header'], 'custom-value')


class TestThreadLifecycle(unittest.TestCase):
    """Test thread lifecycle management"""

    def test_thread_start_and_stop(self):
        """Test that thread starts and stops gracefully"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
        )
        config = FilterEventSink.normalize_config(config)

        thread = EventSinkThread(event_queue=Queue(), config=config, stop_evt=Event())

        # Start thread
        thread.start()
        self.assertTrue(thread.is_alive())

        # Stop thread
        thread.stop()
        self.assertFalse(thread.is_alive())

    @responses.activate
    def test_final_flush_on_shutdown(self):
        """Test that remaining events are flushed on shutdown"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com/filter-pipelines/test/events',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            flush_interval_seconds=100,  # Very long to prevent time-based flush
        )
        config = FilterEventSink.normalize_config(config)

        thread = EventSinkThread(event_queue=Queue(), config=config, stop_evt=Event())

        # Add events to batch (but don't flush)
        event = {'topic': 'main', 'data': {'test': 'data'}}
        thread._add_event_to_batch(event)

        # Start and stop thread
        thread.start()
        time.sleep(0.1)  # Let thread initialize
        thread.stop()

        # Should have flushed on shutdown
        self.assertEqual(len(responses.calls), 1)


if __name__ == '__main__':
    unittest.main()
