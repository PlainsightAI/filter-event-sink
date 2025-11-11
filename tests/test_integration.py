#!/usr/bin/env python

"""
Integration tests for Event Sink Filter

Tests the complete end-to-end flow from frames to API
"""

import gzip
import json
import multiprocessing
import time
import unittest

import numpy as np
import responses
from openfilter.filter_runtime.frame import Frame

from filter_event_sink import FilterEventSink, FilterEventSinkConfig


class TestFilterIntegration(unittest.TestCase):
    """Integration tests for the full filter"""

    @responses.activate
    def test_end_to_end_flow(self):
        """Test complete flow from frame to API post"""
        responses.add(
            responses.POST,
            'https://api.example.com/filter-pipelines/test/events',
            status=202,
        )

        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com/filter-pipelines/test/events',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            flush_interval_seconds=0.5,  # Fast flush for testing
        )

        filter_instance = FilterEventSink(config)
        config = filter_instance.normalize_config(config)
        filter_instance.config = config
        filter_instance.setup(config)

        try:
            # Process frame with events (using new topic pattern)
            frame = Frame(
                data={
                    'detections': [
                        {'type': 'detection', 'class': 'person'},
                        {'type': 'detection', 'class': 'vehicle'},
                    ],
                    'count': 2,
                }
            )
            frames = {'ObjectDetector__detections': frame}

            result = filter_instance.process(frames)

            # Output filter returns None
            self.assertIsNone(result)

            # Wait for batch to flush (longer time to ensure thread processes events)
            time.sleep(2.0)

            # Should have posted to API
            self.assertGreaterEqual(
                len(responses.calls),
                1,
                f"No API calls made. Queue size: {filter_instance.event_queue.qsize()}",
            )

            # Verify payload
            request = responses.calls[0].request
            if request.headers.get('Content-Encoding') == 'gzip':
                payload = gzip.decompress(request.body)
            else:
                payload = request.body

            events = json.loads(payload)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['pipelineid'], 'test-pipeline-id')
            self.assertEqual(events[0]['filtername'], 'ObjectDetector')
            self.assertEqual(events[0]['filtertopic'], 'detections')

        finally:
            filter_instance.shutdown()

    def test_output_filter_returns_none(self):
        """Test that output filter returns None"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
        )

        filter_instance = FilterEventSink(config)
        config = filter_instance.normalize_config(config)
        filter_instance.config = config
        filter_instance.setup(config)

        try:
            # Create frame with image
            image = np.zeros((100, 100, 3), dtype=np.uint8)
            frame = Frame(image=image, data={'test': 'data'}, format='BGR')
            frames = {'TestFilter__main': frame}

            result = filter_instance.process(frames)

            # Output filter returns None
            self.assertIsNone(result)

        finally:
            filter_instance.shutdown()


try:
    multiprocessing.set_start_method('spawn')  # CUDA doesn't like fork()
except Exception:
    pass


if __name__ == '__main__':
    unittest.main()
