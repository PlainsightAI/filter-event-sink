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


class TestFrameIdExtraction(unittest.TestCase):
    """Test frame ID extraction from _filter hidden topic (TI-130)"""

    def setUp(self):
        """Set up test filter instance"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
        )
        self.config = FilterEventSink.normalize_config(config)
        self.filter = FilterEventSink(self.config)
        self.filter.event_queue = Queue()

    def test_extract_frame_id_from_filter_topic(self):
        """Test extraction of frame id from standalone _filter topic"""
        frames = {
            '_filter': Frame(data={'id': 42}),
            'Detector__events': Frame(data={'class': 'person'}),
        }

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['id'], 42)
        self.assertEqual(events[0]['data']['class'], 'person')

    def test_extract_frame_id_from_prefixed_filter_topic(self):
        """Test extraction of frame id from source-prefixed _filter topic"""
        frames = {
            'VideoIn___filter': Frame(data={'id': 123}),
            'Detector__events': Frame(data={'class': 'vehicle'}),
        }

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['id'], 123)
        self.assertEqual(events[0]['data']['class'], 'vehicle')

    def test_frame_id_attached_to_all_events(self):
        """Test that frame id is attached to all events from same frame batch"""
        frames = {
            '_filter': Frame(data={'id': 99}),
            'Detector1__events': Frame(data={'class': 'person'}),
            'Detector2__alerts': Frame(data={'level': 'high'}),
        }
        self.filter.config.event_topics = ['*']

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 2)
        for event in events:
            self.assertEqual(event['data']['id'], 99)

    def test_no_filter_topic_present(self):
        """Test extraction when no _filter topic is present"""
        frames = {
            'Detector__events': Frame(data={'class': 'person'}),
        }

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertNotIn('id', events[0]['data'])

    def test_filter_topic_not_processed_as_event(self):
        """Test that _filter topic itself is not processed as an event"""
        frames = {
            '_filter': Frame(data={'id': 42}),
        }
        self.filter.config.event_topics = ['*']

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 0)

    def test_frame_id_array_preserved(self):
        """Test that array of frame IDs is preserved"""
        frames = {
            '_filter': Frame(data={'id': [1, 2, 3]}),
            'Detector__events': Frame(data={'class': 'person'}),
        }

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['id'], [1, 2, 3])

    def test_additional_filter_metadata_preserved(self):
        """Test that additional metadata from _filter is preserved"""
        frames = {
            '_filter': Frame(data={'id': 42, 'extra_field': 'value'}),
            'Detector__events': Frame(data={'class': 'person'}),
        }

        events = self.filter._extract_events(frames)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['data']['id'], 42)
        self.assertEqual(events[0]['data']['extra_field'], 'value')

    def test_non_hidden_filter_topic_processed(self):
        """Test that non-hidden topic named 'filter' is processed as event"""
        frames = {
            'Detector__filter': Frame(data={'result': 'filtered'}),
        }
        self.filter.config.event_topics = ['*']

        events = self.filter._extract_events(frames)

        # 'Detector__filter' is NOT hidden (_filter), so it should be processed
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['topic'], 'filter')


class TestKeyDeduplication(unittest.TestCase):
    """Test key collision handling when merging filter metadata (TI-130)"""

    def setUp(self):
        """Set up test filter instance"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
        )
        self.config = FilterEventSink.normalize_config(config)
        self.filter = FilterEventSink(self.config)
        self.filter.event_queue = Queue()

    def test_no_collision(self):
        """Test merge when no key collision exists"""
        frame_data = {'class': 'person'}
        filter_metadata = {'id': 42}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        self.assertEqual(merged['class'], 'person')
        self.assertEqual(merged['id'], 42)

    def test_collision_frame_data_wins(self):
        """Test that frame data takes precedence on collision"""
        frame_data = {'id': 'detector-internal-id', 'class': 'person'}
        filter_metadata = {'id': 42}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        self.assertEqual(merged['id'], 'detector-internal-id')
        self.assertEqual(merged['filter_id'], 42)

    def test_collision_filter_prefix_added(self):
        """Test that colliding filter key is preserved with prefix"""
        frame_data = {'id': 'original'}
        filter_metadata = {'id': 'from-filter'}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        self.assertIn('filter_id', merged)
        self.assertEqual(merged['filter_id'], 'from-filter')

    def test_empty_filter_metadata(self):
        """Test merge with empty filter metadata"""
        frame_data = {'class': 'person'}
        filter_metadata = {}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        self.assertEqual(merged, frame_data)

    def test_non_dict_frame_data(self):
        """Test merge when frame data is not a dict"""
        frame_data = 'string data'
        filter_metadata = {'id': 42}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        self.assertEqual(merged['data'], 'string data')
        self.assertEqual(merged['id'], 42)

    def test_multiple_collisions(self):
        """Test handling of multiple key collisions"""
        frame_data = {'id': 'frame-id', 'timestamp': 'frame-ts'}
        filter_metadata = {'id': 42, 'timestamp': 'filter-ts', 'extra': 'value'}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        self.assertEqual(merged['id'], 'frame-id')
        self.assertEqual(merged['filter_id'], 42)
        self.assertEqual(merged['timestamp'], 'frame-ts')
        self.assertEqual(merged['filter_timestamp'], 'filter-ts')
        self.assertEqual(merged['extra'], 'value')

    def test_prefixed_key_already_exists(self):
        """Test when prefixed key already exists in frame data"""
        frame_data = {'id': 'frame-id', 'filter_id': 'existing'}
        filter_metadata = {'id': 42}

        merged = self.filter._merge_event_data(frame_data, filter_metadata)

        # Original frame data preserved, filter_id collision not overwritten
        self.assertEqual(merged['id'], 'frame-id')
        self.assertEqual(merged['filter_id'], 'existing')


if __name__ == '__main__':
    unittest.main()
