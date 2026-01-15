# Event Sink Filter Pipeline Demo

This demo shows how to use the `filter-event-sink` in an OpenFilter pipeline with the [openfilter-pipelines-controller](https://github.com/PlainsightAI/openfilter-pipelines-controller) v0.2.0+.

## Overview

This pipeline example demonstrates:
- Reading from an RTSP video stream
- Processing video through a face blur filter
- Sending events from multiple filters to the Plainsight API using the event sink filter
- Visualizing the output with WebVis

## Prerequisites

1. **Kubernetes cluster** with the [openfilter-pipelines-controller](https://github.com/PlainsightAI/openfilter-pipelines-controller) v0.2.0+ installed
2. **Plainsight API token** for authentication
3. **RTSP video source** (the example uses `rtsp-video-stream:8554/stream`)

## Setup Instructions

### 1. Create the Namespace

```bash
kubectl create namespace pipeline-demo
```

### 2. Create the API Token Secret

You need to create a Kubernetes secret containing your Plainsight API token:

```bash
kubectl create secret generic -n pipeline-demo plainsight-api-token --from-literal=token=<your_token>
```

Replace `<your_token>` with your actual Plainsight API token.

### 3. Update Configuration (Optional)

**Edit [pipelinesource.yaml](pipelinesource.yaml)** if you need to customize:
- **RTSP source** (lines 6-9): Update the host, port, and path for your video source
- **RTSP credentials** (lines 10-11): Uncomment and configure if your stream requires authentication

**Edit [pipeline.yaml](pipeline.yaml)** if you need to customize:
- **API endpoint** (line 42): Update the endpoint URL for your project
- **API custom headers** (line 44): Update the X-Scope-OrgID header with your organization ID

### 4. Deploy the Resources

Apply the resources in order:

```bash
# Apply the pipeline definition (filter recipe)
kubectl apply -f pipeline.yaml -n pipeline-demo

# Apply the pipeline source (RTSP configuration)
kubectl apply -f pipelinesource.yaml -n pipeline-demo

# Create a pipeline instance to execute the pipeline
kubectl apply -f pipelineinstance.yaml -n pipeline-demo
```

Or apply all at once:

```bash
kubectl apply -f . -n pipeline-demo
```

## Monitoring

### Check Resource Status

```bash
kubectl get pipelines -n pipeline-demo
kubectl get pipelinesources -n pipeline-demo
kubectl get pipelineinstances -n pipeline-demo
```

### View Logs

Check logs for the event sink filter:

```bash
kubectl logs -n pipeline-demo -l filter=event-sink -f
```

Check logs for other filters:

```bash
# Video input
kubectl logs -n pipeline-demo -l filter=video-in -f

# Face blur
kubectl logs -n pipeline-demo -l filter=face-blur -f

# WebVis
kubectl logs -n pipeline-demo -l filter=webvis -f
```

### Access WebVis

The pipeline exposes a WebVis service on port 8080. Port-forward to access it locally:

```bash
kubectl port-forward -n pipeline-demo svc/pipeline-rtsp-event-sink-webvis 8080:8080
```

Then open http://localhost:8080 in your browser.

## Pipeline Architecture

```
RTSP Source -> video-in -> face-blur -> webvis
                  |           |
                  +--- event-sink ---> Plainsight API
```

The event sink filter:
- Subscribes to events from both `video-in` and `face-blur` filters
- Enriches events with source information (VideoIn and FaceBlur labels)
- Sends events to the configured Plainsight API endpoint
- Uses the API token from the Kubernetes secret for authentication

## Resource Structure (v0.2.0)

The openfilter-pipelines-controller v0.2.0 introduces a separation of concerns:

- **Pipeline** (`pipeline.yaml`): Defines the filter recipe (reusable)
- **PipelineSource** (`pipelinesource.yaml`): Defines the input source configuration (reusable)
- **PipelineInstance** (`pipelineinstance.yaml`): Executes a Pipeline with a specific PipelineSource

This allows you to:
- Reuse the same Pipeline with different sources
- Reuse the same source with different Pipelines
- Create multiple instances of the same Pipeline+Source combination

## Cleanup

To remove the pipeline and all associated resources:

```bash
kubectl delete -f pipelineinstance.yaml -n pipeline-demo
kubectl delete -f pipelinesource.yaml -n pipeline-demo
kubectl delete -f pipeline.yaml -n pipeline-demo
kubectl delete secret plainsight-api-token -n pipeline-demo
kubectl delete namespace pipeline-demo
```

Or delete all at once:

```bash
kubectl delete -f . -n pipeline-demo
kubectl delete secret plainsight-api-token -n pipeline-demo
kubectl delete namespace pipeline-demo
```

## Troubleshooting

### Pipeline Not Starting

Check the controller logs:

```bash
kubectl logs -n openfilter-pipelines-system deployment/openfilter-pipelines-controller-manager
```

### Authentication Errors

Verify the secret exists and contains the correct token:

```bash
kubectl get secret plainsight-api-token -n pipeline-demo -o yaml
```

### Check PipelineInstance Status

```bash
kubectl describe pipelineinstance pipelineinstance-rtsp-event-sink -n pipeline-demo
```
