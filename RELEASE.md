# Changelog
Event Sink filter release notes

## [Unreleased]

## v1.1.2 - 2026-01-23

### Added
- Promote `pipeline_instance_id` from `_filter` topic to CloudEvents `pipelineinstanceid` extension field
  - Enables correlation of events across pipeline instances
  - Follows same pattern as `frameid` extraction

## v1.1.1 - 2026-01-21

### Fixed
- updated dependencies to latest versions
- CVE: update `opencv-python-headless` to 4.13.0 (fixes ffmpeg security vulnerability) (OpenFilter dependency update)

## v1.1.0 - 2026-01-14

### Changed
- Updated demo pipeline for openfilter-pipelines-controller v0.2.0
- Updated security scan workflow

### Added
- Extract frame ID from _filter topic and attach to events

### Fixed
- Fix workflow dependencies (publish-to-pypi -> publish-docker)
- docker push in create release workflow

## v1.0.3 - 2025-12-17

### Fixed
- Docker image tag

## v1.0.2 - 2025-12-17

### Fixed
- Docker image build

## v1.0.1 - 2025-11-11

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
