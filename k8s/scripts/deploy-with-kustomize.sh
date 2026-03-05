#!/bin/bash

set -e

GPU_COUNT=${1:-1}

if [[ ! "$GPU_COUNT" =~ ^[1248]$ ]]; then
  echo "Error: GPU_COUNT must be 1, 2, 4, or 8"
  echo "Usage: $0 <gpu-count>"
  echo "Example: $0 4"
  exit 1
fi

OVERLAY_DIR="kustomize/overlays/gpu-${GPU_COUNT}"

if [ ! -d "$OVERLAY_DIR" ]; then
  echo "Error: Overlay directory $OVERLAY_DIR not found"
  exit 1
fi

echo "Deploying with Kustomize: $GPU_COUNT GPU(s)..."

kubectl apply -k "$OVERLAY_DIR"

DEPLOYMENT_NAME="gpu-workload-${GPU_COUNT}gpu"

echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/$DEPLOYMENT_NAME --timeout=300s

echo "Deployment successful!"
kubectl get deployment $DEPLOYMENT_NAME
kubectl get pods -l app=gpu-workload,gpu-count=$GPU_COUNT
