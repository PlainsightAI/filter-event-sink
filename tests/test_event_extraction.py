#!/usr/bin/env python

"""
Unit tests for event extraction from frames

Tests various patterns for extracting events from frame data
"""

import unittest
from queue import Queue

from openfilter.filter_runtime.frame import Frame

from filter_event_sink import FilterEventSink, FilterEventSinkConfig


class TestEventExtraction(unittest.TestCase):
    """Test event extraction from frames"""

    def setUp(self):
        """Set up test filter instance"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
        )
        self.config = FilterEventSink.normalize_config(config)
        self.filter = FilterEventSink(self.config)
        self.filter.event_queue = Queue()  # Mock queue

    def test_extract_from_topic_with_filter_name(self):
        """Test extraction from topic with filter name pattern"""
        frame = Frame(
            data={
                'count': 2,
                'detections': [
                    {'type': 'detection', 'class': 'person'},
                    {'type': 'detection', 'class': 'vehicle'},
                ],
            }
        )
        frames = {'ObjectDetector__detections': frame}

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['filter_name'], 'ObjectDetector')
        self.assertEqual(events[0]['topic'], 'detections')
        self.assertEqual(events[0]['data']['count'], 2)

    def test_extract_from_simple_topic(self):
        """Test extraction from simple topic (no __ separator)"""
        frame = Frame(data={'type': 'alert', 'message': 'Motion detected'})
        frames = {'AlertFilter': frame}

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['filter_name'], 'AlertFilter')
        self.assertEqual(events[0]['topic'], 'main')
        self.assertEqual(events[0]['data']['message'], 'Motion detected')

    def test_extract_entire_frame_data(self):
        """Test extraction of entire frame.data as event data"""
        frame = Frame(
            data={
                'detections': [
                    {'box': [0, 0, 100, 100], 'class': 'person', 'score': 0.95},
                    {'box': [200, 200, 50, 50], 'class': 'vehicle', 'score': 0.87},
                ],
                'count': 2,
            }
        )
        frames = {'Detector__main': frame}

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['count'], 2)
        self.assertEqual(len(events[0]['data']['detections']), 2)

    def test_extract_full_frame_data_pattern(self):
        """Test extraction of entire frame.data as event"""
        frame = Frame(
            data={'count': 5, 'classes': ['person', 'vehicle'], 'custom_field': 'value'}
        )
        frames = {'main': frame}

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['count'], 5)

    def test_all_frame_data_included(self):
        """Test that all frame data is included in event"""
        frame = Frame(
            data={
                'meta': {
                    'count': 5,
                },
                'custom_field': 'value',
            }
        )
        frames = {'Filter__topic': frame}

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['meta']['count'], 5)
        self.assertEqual(events[0]['data']['custom_field'], 'value')

    def test_topic_filtering_wildcard(self):
        """Test wildcard topic filtering (all except _metrics)"""
        frame1 = Frame(data={'type': 'test'})
        frame2 = Frame(data={'type': 'metric'})
        # Note: filtering happens on full topic name, not extracted topic
        frames = {'detections': frame1, '_metrics': frame2}

        self.filter.config.event_topics = ['*']
        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        # When topic has no __, filter_name is the full topic, topic defaults to 'main'
        self.assertEqual(events[0]['filter_name'], 'detections')
        self.assertEqual(events[0]['topic'], 'main')

    def test_topic_filtering_explicit(self):
        """Test explicit topic filtering"""
        frame1 = Frame(data={'type': 'test1'})
        frame2 = Frame(data={'type': 'test2'})
        frame3 = Frame(data={'type': 'test3'})
        # Note: filtering happens on full topic name (frame key), not extracted topic
        frames = {
            'Filter1__detections': frame1,
            'Filter2__alerts': frame2,
            'Filter3__other': frame3,
        }

        # Must use full topic names for filtering to work
        self.filter.config.event_topics = [
            'Filter1__detections',
            'Filter2__alerts',
        ]
        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 2)
        # The extracted topics (after __) should be detections and alerts
        topics = {e['topic'] for e in events}
        self.assertEqual(topics, {'detections', 'alerts'})


if __name__ == '__main__':
    unittest.main()
