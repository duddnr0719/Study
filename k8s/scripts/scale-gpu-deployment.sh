#!/bin/bash

set -e

DEPLOYMENT_NAME=$1
NEW_GPU_COUNT=$2

if [ -z "$DEPLOYMENT_NAME" ] || [ -z "$NEW_GPU_COUNT" ]; then
  echo "Usage: $0 <deployment-name> <new-gpu-count>"
  echo "Example: $0 gpu-workload 4"
  exit 1
fi

if [[ ! "$NEW_GPU_COUNT" =~ ^[1248]$ ]]; then
  echo "Error: GPU_COUNT must be 1, 2, 4, or 8"
  exit 1
fi

echo "Scaling $DEPLOYMENT_NAME to $NEW_GPU_COUNT GPU(s)..."

MEMORY=$((NEW_GPU_COUNT * 8))Gi
CPU=$((NEW_GPU_COUNT * 4))

kubectl patch deployment $DEPLOYMENT_NAME --type='json' -p="[
  {\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/nvidia.com~1gpu\", \"value\": \"$NEW_GPU_COUNT\"},
  {\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/requests/nvidia.com~1gpu\", \"value\": \"$NEW_GPU_COUNT\"},
  {\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/requests/memory\", \"value\": \"$MEMORY\"},
  {\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/requests/cpu\", \"value\": \"$CPU\"}
]"

echo "Waiting for rollout to complete..."
kubectl rollout status deployment/$DEPLOYMENT_NAME --timeout=300s

echo "Scaling complete!"
kubectl get deployment $DEPLOYMENT_NAME
kubectl get pods -l app=gpu-workload
