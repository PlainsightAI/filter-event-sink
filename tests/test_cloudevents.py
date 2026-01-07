#!/usr/bin/env python

"""
Unit tests for CloudEvent building

Tests CloudEvent v1.0 compliance and Plainsight extensions
"""

import unittest

from filter_event_sink import build_cloudevent


class TestCloudEventBuilding(unittest.TestCase):
    """Test CloudEvent v1.0 compliant event building"""

    def test_cloudevent_required_fields(self):
        """Test that all required CloudEvent fields are present"""
        event = {
            'topic': 'detections',
            'data': {'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        # Required CloudEvents v1.0 fields
        self.assertIn('id', cloudevent)
        self.assertIn('type', cloudevent)
        self.assertIn('source', cloudevent)
        self.assertIn('specversion', cloudevent)
        self.assertEqual(cloudevent['specversion'], '1.0')
        self.assertIn('time', cloudevent)

    def test_cloudevent_plainsight_extensions(self):
        """Test that required Plainsight extensions are present"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'detections',
            'data': {'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['pipelineid'], 'test-pipeline-id')
        self.assertEqual(cloudevent['filtername'], 'TestFilter')
        self.assertEqual(cloudevent['filtertopic'], 'detections')

    def test_cloudevent_type_always_generic(self):
        """Test that event type is always generic"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'main',
            'data': {'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['type'], 'com.plainsight.event.generic')

    def test_cloudevent_type_default_generic(self):
        """Test that event type defaults to generic"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'main',
            'data': {'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['type'], 'com.plainsight.event.generic')

    def test_cloudevent_source_format(self):
        """Test CloudEvent source format"""
        event = {'filter_name': 'TestFilter', 'topic': 'main', 'data': {}}

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(
            cloudevent['source'], 'filter://test-pipeline-id/TestFilter/main'
        )

    def test_cloudevent_timestamp_generation(self):
        """Test that timestamp is generated if not provided"""
        event = {'filter_name': 'TestFilter', 'topic': 'main', 'data': {}}

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        # Should have a timestamp in ISO format with Z suffix
        self.assertIn('time', cloudevent)
        self.assertTrue(cloudevent['time'].endswith('Z'))

    def test_cloudevent_filter_name_from_event(self):
        """Test that filter_name comes from event"""
        event = {'filter_name': 'UpstreamFilter', 'topic': 'main', 'data': {}}

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['filtername'], 'UpstreamFilter')
        self.assertEqual(
            cloudevent['source'], 'filter://test-pipeline-id/UpstreamFilter/main'
        )


class TestCloudEventFrameId(unittest.TestCase):
    """Test frame ID extension field in CloudEvents (TI-130)"""

    def test_frame_id_promoted_to_extension(self):
        """Test that frame id from data is promoted to extension field"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'events',
            'data': {'id': 42, 'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['frameid'], 42)
        # id should also remain in data
        self.assertEqual(cloudevent['data']['id'], 42)

    def test_frame_id_array_promoted(self):
        """Test that array of frame IDs is promoted to extension"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'events',
            'data': {'id': [1, 2, 3], 'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['frameid'], [1, 2, 3])

    def test_no_frame_id_no_extension(self):
        """Test that frameid extension is absent when no id in data"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'events',
            'data': {'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertNotIn('frameid', cloudevent)

    def test_non_dict_data_no_frame_id(self):
        """Test that non-dict data doesn't cause errors"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'events',
            'data': 'string data',
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertNotIn('frameid', cloudevent)

    def test_frame_id_zero_is_valid(self):
        """Test that frame id of 0 is still promoted"""
        event = {
            'filter_name': 'TestFilter',
            'topic': 'events',
            'data': {'id': 0, 'class': 'person'},
        }

        cloudevent = build_cloudevent(
            event=event,
            pipeline_id='test-pipeline-id',
            event_source_base='filter://',
        )

        self.assertEqual(cloudevent['frameid'], 0)


if __name__ == '__main__':
    unittest.main()
