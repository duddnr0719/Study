#!/bin/bash

set -e

GPU_COUNT=${1:-1}
POD_NAME=${2:-gpu-pod-${GPU_COUNT}x}

if [[ ! "$GPU_COUNT" =~ ^[1248]$ ]]; then
  echo "Error: GPU_COUNT must be 1, 2, 4, or 8"
  echo "Usage: $0 <gpu-count> [pod-name]"
  echo "Example: $0 2 my-gpu-pod"
  exit 1
fi

PRESET_FILE="presets/gpu-${GPU_COUNT}.yaml"

if [ ! -f "$PRESET_FILE" ]; then
  echo "Error: Preset file $PRESET_FILE not found"
  exit 1
fi

echo "Deploying GPU pod with $GPU_COUNT GPU(s)..."
echo "Pod name: $POD_NAME"

kubectl apply -f "$PRESET_FILE"

if [ -n "$2" ]; then
  kubectl patch pod "gpu-pod-${GPU_COUNT}x" -p "{\"metadata\":{\"name\":\"$POD_NAME\"}}" --dry-run=client -o yaml | kubectl apply -f -
fi

echo "Waiting for pod to be ready..."
kubectl wait --for=condition=Ready pod/$POD_NAME --timeout=300s

echo "Pod deployed successfully!"
kubectl get pod "$POD_NAME" -o wide
