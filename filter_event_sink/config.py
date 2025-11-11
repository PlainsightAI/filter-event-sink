"""
Configuration for Event Sink Filter
"""

import logging
import socket
import uuid

from openfilter.filter_runtime.filter import FilterConfig

logger = logging.getLogger(__name__)


class FilterEventSinkConfig(FilterConfig):
    """Configuration for Event Sink Filter"""

    # API Configuration (required)
    # api_endpoint should be the full URL including pipeline name and query params
    # Example: "https://api.prod.plainsight.tech/filter-pipelines/my-pipeline/events?project=uuid"
    # Environment variable: FILTER_API_ENDPOINT
    api_endpoint: str = ''

    # API token for authentication
    # Environment variable: FILTER_API_TOKEN
    api_token: str = ''

    # Custom HTTP headers (optional)
    # Format: list of "Header-Name: value" strings or dict
    # Example: ["X-Scope-OrgID: 48eec17d-3089-4d13-a107-24f5f4cf84c7", "X-Custom: value"]
    # Environment variable: FILTER_API_CUSTOM_HEADERS
    api_custom_headers: list[str] | dict[str, str] | str = []

    # Event Collection
    event_topics: list[str] | str = ['*']  # Topics to collect events from

    # Batch Configuration
    max_batch_size_bytes: int = 5 * 1024 * 1024  # 5 MiB (API limit)
    max_batch_events: int = 1000  # Max events per batch
    flush_interval_seconds: float = 5.0  # Max time between flushes

    # CloudEvent Metadata
    filter_name: str = 'EventSink'
    event_source_base: str = 'filter://'

    # HTTP Configuration
    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_base: float = 2.0

    # Compression
    enable_gzip: bool = True
    gzip_compression_level: int = 6

    # Queue Configuration
    event_queue_size: int = 10000

    @classmethod
    def normalize(cls, config: 'FilterEventSinkConfig') -> 'FilterEventSinkConfig':
        """Normalize and validate configuration"""
        # Validate required fields
        if not config.api_endpoint:
            raise ValueError("api_endpoint is required (set FILTER_API_ENDPOINT)")
        if not config.api_token:
            raise ValueError("api_token is required (set FILTER_API_TOKEN)")

        # Validate pipeline_id is present (set by openfilter runtime or config)
        if not hasattr(config, 'pipeline_id') or not config.pipeline_id:
            logger.warning(
                "pipeline_id not found in config, will use a auto-generated one"
            )
            config.pipeline_id = f'{socket.gethostname()}-{uuid.uuid4()}'

        # Normalize topic filter (convert string to list)
        if isinstance(config.event_topics, str):
            config.event_topics = [t.strip() for t in config.event_topics.split(',')]

        # Normalize api_custom_headers (convert to dict)
        if isinstance(config.api_custom_headers, str):
            # Handle empty string as no headers
            if not config.api_custom_headers.strip():
                config.api_custom_headers = {}
            else:
                # Single header string: "Header: value"
                config.api_custom_headers = [config.api_custom_headers]
        if isinstance(config.api_custom_headers, list):
            # List of "Header: value" strings -> convert to dict
            headers_dict = {}
            for header in config.api_custom_headers:
                # Skip empty strings
                if not header or not header.strip():
                    continue
                if ':' in header:
                    key, value = header.split(':', 1)
                    headers_dict[key.strip()] = value.strip()
                else:
                    logger.warning(
                        f"Invalid custom header format (missing ':'): {header}"
                    )
            config.api_custom_headers = headers_dict
        elif not isinstance(config.api_custom_headers, dict):
            config.api_custom_headers = {}

        # Validate and cap limits
        if config.max_batch_size_bytes > 5 * 1024 * 1024:
            logger.warning(
                f"max_batch_size_bytes ({config.max_batch_size_bytes}) exceeds API limit (5 MiB), "
                f"capping to 5 MiB"
            )
            config.max_batch_size_bytes = 5 * 1024 * 1024

        if config.max_batch_events > 1000:
            logger.warning(
                f"max_batch_events ({config.max_batch_events}) is very high, "
                f"consider reducing for better latency"
            )

        # Validate compression level
        if not (1 <= config.gzip_compression_level <= 9):
            logger.warning(
                f"Invalid gzip_compression_level ({config.gzip_compression_level}), "
                f"setting to default (6)"
            )
            config.gzip_compression_level = 6

        # validate sources
        for source in config.sources or []:
            # validate that all sources use doubly ephemeral source identifier (??)
            if '??' not in source:
                raise ValueError(
                    f"Source {source} does not use doubly ephemeral source identifier"
                )
            # validates that all sources remaps the topic
            if '>' not in source:
                raise ValueError(f"Source {source} does not remap the topic")

        return config
