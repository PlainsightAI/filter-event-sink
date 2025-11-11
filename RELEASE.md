# Changelog
Event Sink filter release notes

## [Unreleased]


## v1.0.0 - 2025-11-11

### Added
- Initial Release: Event Sink filter for CloudEvents ingestion
- Dual-thread design: main filter thread + background HTTP posting thread
- CloudEvents v1.0 compliant event generation with Plainsight extensions
- Intelligent batch accumulation with size, count, and time-based flush triggers
- Gzip compression for efficient network bandwidth usage (70-80% reduction)
- Automatic retry with exponential backoff for resilient delivery
- Topic-based event filtering
- Configurable via environment variables
- Comprehensive unit tests with >85% code coverage
- Graceful shutdown with final event flush
- HTTP connection pooling for optimal performance
- Bounded event queue to prevent memory overflow
