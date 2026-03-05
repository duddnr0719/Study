#!/usr/bin/env python3

import argparse
import sys
import subprocess
import yaml

def create_gpu_pod_manifest(name, gpu_count, image, namespace="default"):
    memory = f"{gpu_count * 8}Gi"
    cpu = str(gpu_count * 4)
    
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {
                "app": "gpu-workload",
                "gpu-count": str(gpu_count)
            }
        },
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "gpu-container",
                "image": image,
                "command": ["sleep", "infinity"],
                "resources": {
                    "limits": {
                        "nvidia.com/gpu": str(gpu_count)
                    },
                    "requests": {
                        "nvidia.com/gpu": str(gpu_count),
                        "memory": memory,
                        "cpu": cpu
                    }
                },
                "env": [
                    {"name": "NVIDIA_VISIBLE_DEVICES", "value": "all"},
                    {"name": "NVIDIA_DRIVER_CAPABILITIES", "value": "compute,utility"}
                ]
            }],
            "nodeSelector": {
                "accelerator": "nvidia-gpu"
            },
            "tolerations": [{
                "key": "nvidia.com/gpu",
                "operator": "Exists",
                "effect": "NoSchedule"
            }]
        }
    }
    
    return manifest

def main():
    parser = argparse.ArgumentParser(description="Create GPU pod with dynamic GPU allocation")
    parser.add_argument("name", help="Pod name")
    parser.add_argument("gpu_count", type=int, choices=[1, 2, 4, 8], help="Number of GPUs (1, 2, 4, or 8)")
    parser.add_argument("--image", default="nvidia/cuda:12.3.0-runtime-ubuntu22.04", help="Container image")
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--dry-run", action="store_true", help="Print manifest without applying")
    
    args = parser.parse_args()
    
    manifest = create_gpu_pod_manifest(args.name, args.gpu_count, args.image, args.namespace)
    manifest_yaml = yaml.dump(manifest, default_flow_style=False)
    
    if args.dry_run:
        print(manifest_yaml)
        return 0
    
    print(f"Creating pod '{args.name}' with {args.gpu_count} GPU(s)...")
    
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=manifest_yaml.encode(),
            capture_output=True,
            check=True
        )
        print(result.stdout.decode())
        print(f"Pod created successfully!")
        
        subprocess.run(["kubectl", "get", "pod", args.name, "-o", "wide"])
        
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.decode()}", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
