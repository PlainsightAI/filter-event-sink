#!/usr/bin/env python

"""
Unit tests for FilterEventSinkConfig

Tests configuration normalization and validation
"""

import unittest

from filter_event_sink import FilterEventSink, FilterEventSinkConfig


class TestFilterEventSinkConfig(unittest.TestCase):
    """Test configuration normalization and validation"""

    def test_required_fields_validation(self):
        """Test that required fields are validated"""
        config = FilterEventSinkConfig()

        # Missing api_endpoint
        with self.assertRaises(ValueError) as ctx:
            FilterEventSink.normalize_config(config)
        self.assertIn('api_endpoint', str(ctx.exception))

        # Missing api_token
        config.api_endpoint = 'https://api.example.com/filter-pipelines/test/events'
        with self.assertRaises(ValueError) as ctx:
            FilterEventSink.normalize_config(config)
        self.assertIn('api_token', str(ctx.exception))

        # Should succeed with both required fields
        config.api_token = 'ps_test123'
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(
            normalized.api_endpoint,
            'https://api.example.com/filter-pipelines/test/events',
        )
        self.assertEqual(normalized.api_token, 'ps_test123')

    def test_endpoint_used_as_is(self):
        """Test that endpoint URL is used as-is (not modified)"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com/filter-pipelines/test/events?project=uuid',
            api_token='ps_test',
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(
            normalized.api_endpoint,
            'https://api.example.com/filter-pipelines/test/events?project=uuid',
        )

    def test_pipeline_id_warning_if_missing(self):
        """Test that warning is logged if pipeline_id is missing"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com', api_token='ps_test'
        )

        with self.assertLogs('filter_event_sink.config', level='WARNING') as log:
            _ = FilterEventSink.normalize_config(config)
            self.assertTrue(
                any(
                    "pipeline_id not found in config" in message
                    for message in log.output
                )
            )

    def test_topic_list_normalization_from_string(self):
        """Test that topic string is converted to list"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            event_topics='detections,alerts,metrics',
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(normalized.event_topics, ['detections', 'alerts', 'metrics'])

    def test_topic_list_preserved(self):
        """Test that topic list is preserved"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            event_topics=['detections', 'alerts'],
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(normalized.event_topics, ['detections', 'alerts'])

    def test_batch_size_capping(self):
        """Test that batch size is capped to API limit"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            max_batch_size_bytes=10 * 1024 * 1024,  # 10 MiB
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(
            normalized.max_batch_size_bytes, 5 * 1024 * 1024
        )  # Capped to 5 MiB

    def test_gzip_compression_level_validation(self):
        """Test that invalid compression level is reset to default"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            gzip_compression_level=15,  # Invalid
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(normalized.gzip_compression_level, 6)  # Default

    def test_custom_headers_from_string(self):
        """Test that single custom header string is normalized to dict"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            api_custom_headers='X-Scope-OrgID: 48eec17d-3089-4d13-a107-24f5f4cf84c7',
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(
            normalized.api_custom_headers,
            {'X-Scope-OrgID': '48eec17d-3089-4d13-a107-24f5f4cf84c7'},
        )

    def test_custom_headers_from_list(self):
        """Test that list of header strings is normalized to dict"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            api_custom_headers=[
                'X-Scope-OrgID: 48eec17d-3089-4d13-a107-24f5f4cf84c7',
                'X-Custom-Header: custom-value',
            ],
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(
            normalized.api_custom_headers,
            {
                'X-Scope-OrgID': '48eec17d-3089-4d13-a107-24f5f4cf84c7',
                'X-Custom-Header': 'custom-value',
            },
        )

    def test_custom_headers_from_dict(self):
        """Test that dict custom headers are preserved"""
        config = FilterEventSinkConfig(
            api_endpoint='https://api.example.com',
            api_token='ps_test',
            pipeline_id='test-pipeline-id',
            api_custom_headers={
                'X-Scope-OrgID': '48eec17d-3089-4d13-a107-24f5f4cf84c7'
            },
        )
        normalized = FilterEventSink.normalize_config(config)
        self.assertEqual(
            normalized.api_custom_headers,
            {'X-Scope-OrgID': '48eec17d-3089-4d13-a107-24f5f4cf84c7'},
        )


if __name__ == '__main__':
    unittest.main()
