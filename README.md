# Event Sink Filter

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen)]()
[![Version](https://img.shields.io/badge/version-v1.0.0-blue)]()

The **Event Sink Filter** is a production-ready OpenFilter component that collects events from filter pipelines and reliably delivers them to a Plainsight API's CloudEvents ingestion compatible endpoint.

## Features

- **CloudEvents v1.0 Compliant**: Industry-standard event format with Plainsight extensions
- **Intelligent Batch Processing**: Automatic batching based on size (5 MiB), count (1000 events), or time (5s)
- **Gzip Compression**: 70-80% bandwidth reduction for efficient network usage
- **Reliable Delivery**: Exponential backoff retry logic for resilient event delivery
- **Flexible Event Collection**: Multiple extraction patterns, topic filtering
- **Production Ready**: Comprehensive error handling, logging, and graceful shutdown

## Architecture

```
Main Thread (Filter)          Background Thread (EventSinkThread)
─────────────────────         ───────────────────────────────────
Receive frames                Accumulate events from queue
Extract events      ───────→  Check flush conditions:
Queue events                  - Size >= 5 MiB
                              - Count >= 1000
                              - Time >= 5s
                              ↓
                              Build CloudEvents batch
                              Gzip compress
                              HTTP POST to API
                              Retry on failure
```

## Prerequisites

If you are exporting events to the Plainsight API, you'll need to:

- **Plainsight API Token**: Generate an API token from the Plainsight dashboard with `filterpipeline:create` scope
- **Plainsight API Filter Pipeline**: Create a filter pipeline in the Plainsight dashboard

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
make install
```

### 2. Configure Environment

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
# Edit .env with your API credentials
```

### 3. Run Locally

```bash
# Run the filter
source venv/bin/activate
source .env && make run
```

Or in one line:
```bash
source .env && source venv/bin/activate && make run
```

### 4. Run in Docker

```bash
# Build image
make build-image

# Run with docker-compose
source .env && make run-image
```

## Configuration

### Required Parameters

| Parameter | Environment Variable | Description |
|-----------|---------------------|-------------|
| `api_endpoint` | `FILTER_API_ENDPOINT` | Full API endpoint URL including pipeline name and query params (e.g., `https://api.plainsight.ai/filter-pipelines/my-pipeline/events?project=uuid`) |
| `api_token` | `FILTER_API_TOKEN` | API token (format: `ps_...`) |
| `api_custom_headers` | `FILTER_API_CUSTOM_HEADERS` | Custom HTTP headers (optional, comma-separated "Header: value" pairs, e.g., `"X-Scope-OrgID: uuid"`) |

### Optional Parameters

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `event_topics` | `FILTER_EVENT_TOPICS` | `*` | Topics to collect (comma-separated) |
| `max_batch_size_bytes` | `FILTER_MAX_BATCH_SIZE_BYTES` | `5242880` | Max batch size (5 MiB) |
| `max_batch_events` | `FILTER_MAX_BATCH_EVENTS` | `1000` | Max events per batch |
| `flush_interval_seconds` | `FILTER_FLUSH_INTERVAL_SECONDS` | `5.0` | Max time between flushes |
| `enable_gzip` | `FILTER_ENABLE_GZIP` | `true` | Enable gzip compression |
| `request_timeout_seconds` | `FILTER_REQUEST_TIMEOUT_SECONDS` | `30.0` | HTTP request timeout |
| `max_retries` | `FILTER_MAX_RETRIES` | `3` | Max retry attempts |

## Event Formats

The filter automatically detects and extracts events from `frame.data`.

### Example
```python
frame.data = {
  'meta': {
    'count': 5,
    'classes': ['person', 'vehicle'],
    'custom_field': 'value'
  }
}
```

## CloudEvent Schema

Events are sent as CloudEvents v1.0 with Plainsight extensions:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "com.plainsight.event.generic",
  "source": "filter://macbookpro-lucas.local-0153261e-9551-4e4a-8740-c71b6dc9c506/ObjectDetector/main",
  "specversion": "1.0",
  "time": "2025-10-27T22:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "meta": {
      "count": 5,
      "classes": ["person", "vehicle"],
      "custom_field": "value"
    }
  },
  "pipelineid": "macbookpro-lucas.local-0153261e-9551-4e4a-8740-c71b6dc9c506",
  "filtername": "ObjectDetector",
  "filtertopic": "detections"
}
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
make test

# Run with coverage report
make test-coverage
```

## Deployment

### Docker Compose Example

```yaml
services:
  filter_event_sink:
    image: plainsightai/openfilter-event-sink:v1.0.1
    environment:
      LOG_LEVEL: INFO
      FILTER_ID: EventSink
      FILTER_SOURCES: tcp://upstream_filter:5550??;>VideoIn

      # Event Sink Configuration
      FILTER_API_ENDPOINT: "https://api.prod.plainsight.tech/filter-pipelines/production-line-1/events?project=your-project-uuid"
      FILTER_API_TOKEN: "${PLAINSIGHT_API_TOKEN}"
      FILTER_API_CUSTOM_HEADERS: "X-Scope-OrgID: 48eec17d-3089-4d13-a107-24f5f4cf84c7"  # Optional
      FILTER_EVENT_TOPICS: "detections,alerts"
      FILTER_FLUSH_INTERVAL_SECONDS: "5.0"

    volumes:
      - ./cache:/app/cache
      - ./telemetry:/app/telemetry
    networks:
      - filter-network
```

### Publishing Releases

1. Update `VERSION` file with semver tag (e.g., `v1.2.3`)
2. Update `RELEASE.md` with version entry matching `VERSION`
3. Merge to main - CI will:
   - Build and publish Docker image to GAR
   - Build and publish Python wheel to GAR
   - Push docs to documentation sites

## Monitoring

The filter provides structured logging:

- **Info**: Successful batch posts, thread lifecycle
- **Warning**: Retries, queue near capacity
- **Error**: Failed posts, dropped events, auth failures

## Performance

- **Throughput**: 1000+ events/second with batching
- **Memory**: Bounded queue (10,000 events)
- **Network**: 70-80% bandwidth reduction with gzip

## Troubleshooting

### Queue Full Warnings
- **Solution**: Increase `event_queue_size` or reduce event rate
- Events will be dropped when queue is full

### API Authentication Errors (401/403)
- **Solution**: Verify `FILTER_API_TOKEN` is valid and has correct scopes
- Check token expiration

### Network Timeouts
- **Solution**: Increase `request_timeout_seconds`
- Check network connectivity to API endpoint

### Events Not Appearing in BigQuery
- **Solution**: Verify filter pipeline exists in Plainsight
- Check API endpoint URL is correct
- Monitor filter logs for POST errors

## Documentation

- [docs/overview.md](docs/overview.md): User-facing documentation
- [RELEASE.md](RELEASE.md): Release notes and changelog

## License

Copyright © 2025 Plainsight AI

## Support

For issues and questions:
- Create an issue in this repository
- Contact Plainsight support

---

**Version**: v1.0.1
**Status**: Production Ready
**Maintainer**: Plainsight AI
