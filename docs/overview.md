---
title: Event Sink
sidebar_label: Overview
sidebar_position: 1
---

The **Event Sink** filter collects events from filter pipelines and reliably delivers them to a CloudEvents-compatible endpoint for persistence and analytics.

### ✨ Features

- **CloudEvents v1.0 Compliance**
  - Industry-standard event format
  - Rich metadata with Plainsight extensions
  - Structured data for analytics and monitoring

- **Intelligent Batch Processing**
  - Automatic batching based on size, count, or time limits
  - Gzip compression for efficient network usage (70-80% size reduction)
  - Configurable flush intervals for latency vs. throughput balance

- **Reliable Delivery**
  - Background thread architecture for non-blocking operation
  - Automatic retry with exponential backoff
  - Graceful shutdown with final event flush

- **Flexible Event Collection**
  - Topic-based filtering (collect from specific topics or all)

### 🛠️ Use Cases

- **Production Monitoring**: Collect detection events from object detectors for real-time dashboards
- **Anomaly Detection**: Stream alerts and anomalies to BigQuery for analysis
- **Compliance Logging**: Persist all pipeline events for audit trails
- **Performance Analytics**: Track filter performance metrics and statistics
- **Custom Integrations**: Send events to any CloudEvents-compatible endpoint

### 📊 Architecture

The Event Sink filter uses a **dual-thread architecture**:

```
Main Thread (Filter Pipeline)          Background Thread
┌────────────────────┐                 ┌──────────────────┐
│ Receive Frames     │                 │ Accumulate Events│
│        ↓           │                 │        ↓         │
│ Extract Events     │ ──── Queue ───→ │ Batch Events     │
│                    │                 │        ↓         │
│                    │                 │ Gzip Compress    │
│                    │                 │        ↓         │
│                    │                 │ HTTP POST to API │
└────────────────────┘                 └──────────────────┘
```

- **Main thread**: Processes frames at full speed, extracts events, queues them
- **Background thread**: Batches events, compresses, POSTs to API with retry logic

### ⚙️ Configuration

#### Required Parameters

```yaml
FILTER_API_ENDPOINT: "https://api.prod.plainsight.tech/filter-pipelines/my-pipeline/events?project=uuid"
FILTER_API_TOKEN: "ps_..."  # API token from Plainsight dashboard
FILTER_API_CUSTOM_HEADERS: "X-Scope-OrgID: your-org-id"  # Your organization ID
```

#### Optional Parameters

**Event Collection**:
- `FILTER_EVENT_TOPICS`: Topics to collect from (default: `"*"` = all except `_metrics`)

**Batch Configuration**:
- `FILTER_MAX_BATCH_SIZE_BYTES`: Max batch size in bytes (default: `5242880` = 5 MiB)
- `FILTER_MAX_BATCH_EVENTS`: Max events per batch (default: `200`)
- `FILTER_FLUSH_INTERVAL_SECONDS`: Max time between flushes (default: `5.0`)

**CloudEvent Metadata**:
- `FILTER_NAME`: This filter's name (default: `"EventSink"`)

**HTTP Configuration**:
- `FILTER_REQUEST_TIMEOUT_SECONDS`: Request timeout (default: `30.0`)
- `FILTER_MAX_RETRIES`: Max retry attempts (default: `3`)
- `FILTER_RETRY_BACKOFF_BASE`: Backoff multiplier (default: `2.0`)

**Compression**:
- `FILTER_ENABLE_GZIP`: Enable gzip compression (default: `true`)
- `FILTER_GZIP_COMPRESSION_LEVEL`: Compression level 1-9 (default: `6`)

### 📝 Event Formats

The filter automatically detects and extracts events from frame.data:


```python
frame.data = {
    'count': 5,
    'classes': ['person', 'vehicle'],
    'custom_field': 'value'
}
```

### 🔒 Security

- **API Token**: Securely authenticate to Plainsight API
- **HTTPS Only**: All communication over encrypted HTTPS
- **Token Storage**: Use environment variables or secrets manager, never hardcode

### 📈 Performance

- **Latency**: Zero added latency to video pipeline
- **Throughput**: Handles 1000+ events/second with batching
- **Memory**: Bounded queue (10,000 events) prevents memory overflow
- **Network**: 70-80% bandwidth reduction with gzip compression

### 🔍 Monitoring

The filter logs:
- **Info**: Successful batch posts, thread lifecycle
- **Warning**: Retries, queue near capacity
- **Error**: Failed posts, dropped events, auth failures

### 🚀 Deployment Example

```yaml
services:
  event_sink:
    image: containers.openfilter.io/plainsightai/openfilter-event-sink:v1.1.0
    environment:
      LOG_LEVEL: INFO
      FILTER_ID: EventSink
      FILTER_SOURCES: tcp://upstream_filter:5550??;>VideoIn

      # Event Sink Configuration
      FILTER_API_ENDPOINT: "https://api.prod.plainsight.tech/filter-pipelines/my-pipeline/events?project=uuid"
      FILTER_API_TOKEN: "${PLAINSIGHT_API_TOKEN}"
      FILTER_API_CUSTOM_HEADERS: "X-Scope-OrgID: your-org-id"
      FILTER_EVENT_TOPICS: "detections,alerts"
      FILTER_FLUSH_INTERVAL_SECONDS: "5.0"

    volumes:
      - ./cache:/app/cache
      - ./telemetry:/app/telemetry
    networks:
      - filter-network
```

### 📚 CloudEvent Schema

Events are sent as CloudEvents v1.0 with Plainsight extensions:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "com.plainsight.event.generic",
  "source": "filter://run-20251027-123456-abc123/ObjectDetector/main",
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

  "pipelineid": "my-machine-20251027-123456-abc123",
  "filtername": "ObjectDetector",
  "filtertopic": "detections"
}
```

### 🛟 Error Handling

- **Queue Full**: Events dropped with error log (increase `event_queue_size` or reduce event rate)
- **API 5xx**: Automatic retry with exponential backoff
- **API 4xx**: No retry (authentication/validation errors)
- **Network Errors**: Automatic retry with exponential backoff
- **Shutdown**: Final flush attempt, events may be lost if API unavailable

### 💡 Best Practices

1. **Set appropriate flush interval**: Balance latency (fast delivery) vs. efficiency (batch size)
2. **Monitor logs**: Watch for queue full warnings or repeated API failures
3. **Use topic filtering**: Reduce event volume by filtering specific topics
4. **Secure API tokens**: Use secrets management, rotate tokens regularly
5. **Test connectivity**: Verify API endpoint and token before production deployment
