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


if __name__ == '__main__':
    unittest.main()
