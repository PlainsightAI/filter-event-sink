# v1.1.6

- Fix release workflow secret names: `PYPI_API_TOKEN` → `PLAINSIGHT_PYPI_TOKEN`, `DOCKERHUB_TOKEN` → `DOCKERHUB_ACCESS_TOKEN` (org-level secret names). Without this the PyPI / Docker Hub tokens resolved to empty and no package has been published since the migration.
- Bump openfilter dependency to `>=0.1.30`.

# Changelog
Event Sink filter release notes

## [Unreleased]

## v1.1.5 - 2026-04-20

### Changed
- Remove redundant ci.yaml (shared workflow handles PR testing)
- Add push + pull_request triggers to create-release.yaml


## v1.1.4 - 2026-04-20

### Changed
- Replace inline create-release.yaml with shared workflow caller (~13 lines)
- Switch to shared security-scan workflow
- Bump openfilter to >=0.1.27
- Secret names updated to PYPI_API_TOKEN / DOCKERHUB_TOKEN


## v1.1.3 - 2026-03-11

### Fixed
- Relax source validation: sources without doubly ephemeral (`??`) now log a warning instead of raising `ValueError`, allowing the filter to start in environments where the pipeline export does not yet generate the recommended source format

### Changed
- Standardize build path to match public openfilter filters (from v1.1.2)
- Relax openfilter version constraint to `~=0.1.0` (from v1.1.2)

## v1.1.2 - 2026-01-28

### Fixed
- Add missing X11/OpenCV runtime libraries to Dockerfile
  - Fixes `ImportError: libxcb.so.1 cannot open shared object file`
- Update openfilter dependency to 0.1.20

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
