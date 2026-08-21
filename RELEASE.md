# Changelog
Event Sink filter release notes

## [Unreleased]

## v1.1.10 - 2026-08-19

### Changed

- Build the filter image on `openfilter-base:py3.14` (was the prior interpreter). The published wheel supports Python 3.14, so the image now ships 3.14. Running on 3.10–3.13 is unaffected.


## v1.1.9 - 2026-08-18

### Added

- **Promote the source-file identity to a `sourceuri` CloudEvent extension.** When an incoming frame carries `data['meta']['src']` (the entry filter's source-file identity, e.g. a batch object URI stamped via `FILTER_OVERRIDE_SOURCE_URI`), `build_cloudevent` now promotes it to a `sourceuri` extension — mirroring how `frameid` is promoted. A downstream consumer can store it as a typed queryable column, enabling per-source-file attribution of batch pipeline data. Absent for streaming or filters that don't carry `meta.src`.

- **Promote the frame's source-file position (`sourceframe` / `sourceseconds`) as CloudEvent
  extensions.** When a frame carries `data['meta']['src_frame']` / `data['meta']['src_seconds']`
  (VideoIn file sources: the 0-based frame index and the offset in seconds within the source),
  `build_cloudevent` now promotes them alongside `sourceuri`, mirroring `frameid`. CloudEvents has
  no float attribute type, so both are sent as strings for a downstream consumer to parse into
  typed numeric columns. Absent for streaming/webcam and sources with no decoder position.

### Changed

- Update the openfilter dependency to 1.3.0
- Add Python 3.14 support: raise the `requires-python` ceiling to `<3.15` and add 3.14 to the CI
  test matrix (3.10–3.13 unchanged).

## v1.1.8 - 2026-08-10

### Changed

- Build the image on `openfilter-base` (weekly apt-upgraded python-slim) instead of a stale `python:X.Y.Z-slim` pin, clearing the OS-package CVEs the pin carried.
- Update the openfilter dependency to 1.2.2

## v1.1.7 - 2026-08-04

### Changed
- Update `openfilter[all]` to `>=1.2.1`.
- Grant `id-token: write` in the release workflow for keyless (cosign) SBOM attestation.
- Fix RELEASE.md header (stray H1 + duplicated `# Changelog`/`## [Unreleased]` block broke the changelog-parser).
- Pin Docker base image to `python:3.13.14-slim`.
- Point compose utility images at `openfilter-{video-in,webvis}:1.2.1`, and repair the compose env-var defaults/ports mangled by an earlier bad find/replace.
- Update dev-tooling floors and switch to range pins.

## v1.1.6 - 2026-04-23

### Changed
- Update the openfilter dependency to `>=0.1.30`, and align the CI workflow with the shared release gate (source-paths).
- Fix release workflow secret names: `PYPI_API_TOKEN` → `PLAINSIGHT_PYPI_TOKEN`, `DOCKERHUB_TOKEN` → `DOCKERHUB_ACCESS_TOKEN` (org-level secret names). Without this the PyPI / Docker Hub tokens resolved to empty and no package has been published since the migration.

## v1.1.5 - 2026-04-20

### Changed
- Remove redundant ci.yaml (shared workflow handles PR testing)
- Add push + pull_request triggers to create-release.yaml

## v1.1.4 - 2026-04-20

### Changed
- Replace inline create-release.yaml with shared workflow caller (~13 lines)
- Switch to shared security-scan workflow
- Update openfilter to >=0.1.27
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
