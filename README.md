# LLM Deployment on EKS

A production-ready Amazon EKS deployment of Meta-Llama-3.1-8B-Instruct with optimized model loading using S3 caching and vLLM inference.

This project deploys a single LLM service with an OpenAI-compatible API endpoint for text generation and chat completions.

> **⚠️ Before You Begin**: This repository contains hardcoded references to a specific AWS account, VPC, subnets, and S3 bucket. You **must** update these values to match your own AWS environment before deploying. See the [Configuration](#configuration) section for details.

## What is this project?

This repository provides a production-grade Amazon EKS deployment for Meta-Llama-3.1-8B-Instruct with the following features:

- **Amazon EKS cluster** for scalable GPU workloads
- **S3-based model caching** with IRSA for secure, keyless access
- **vLLM inference engine** with OpenAI-compatible API
- **Fast startup times** (3-5 min) using pre-cached models from S3
- **GPU optimization** for g6e.xlarge instances (NVIDIA L40S, 48GB VRAM)
- **LoadBalancer service** for direct API access

### Key Features

| Feature                | Description                                                     |
| ---------------------- | --------------------------------------------------------------- |
| **Model**              | Meta-Llama-3.1-8B-Instruct (16GB model size)                   |
| **Inference Engine**   | vLLM v0.11.0 with OpenAI-compatible API                        |
| **Model Loading**      | S3 + init containers (3-5 min startup)                         |
| **GPU**                | g6e.xlarge (NVIDIA L40S, 48GB VRAM)                            |
| **Context Length**     | 8192 tokens (configurable)                                     |
| **Access Control**     | LoadBalancer with source IP restrictions                       |
| **IAM**                | IRSA (IAM Roles for Service Accounts) for keyless S3 access   |

## Quick Start

### 1. Prerequisites

```bash
# AWS credentials configured
aws configure

# Kubernetes tools
kubectl version --client

# Python 3 (for model upload script)
python3 --version
```

**Required AWS Resources** (must already exist):
- EKS cluster with GPU nodes (g6e.xlarge or similar)
- IAM role for IRSA (S3 access)
- S3 bucket for model storage
- VPC with appropriate networking

> **Note:** This project assumes you have an existing EKS cluster. Use `eksctl` or Terraform to create the cluster separately.

### 2. Upload Model to S3

Before deploying, you need to upload the Meta-Llama-3.1-8B-Instruct model to S3:

```bash
# Set up Python environment for model upload script
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# Set your HuggingFace token (required - you must accept Llama license on HuggingFace first)
export HUGGING_FACE_HUB_TOKEN=hf_your_token_here

# Upload model to S3 (~16GB download + upload)
./scripts/upload-models-to-s3.sh all
```

### 3. Configure Kustomize

The project uses Kustomize for configuration management. Update configuration values in one place:

```bash
# Copy the example config and customize it
cp k8s/config/default-config.env.example k8s/config/default-config.env

# Edit the config file with your values
# Required changes:
# - AWS_ACCOUNT_ID: Your AWS account ID
# - IAM_ROLE_NAME: Your IAM role name (if different)
# - HUGGING_FACE_HUB_TOKEN: Your HuggingFace token
vim k8s/config/default-config.env
```

### 4. Deploy to EKS

Using Kustomize (recommended):

```bash
# Preview what will be deployed
kubectl kustomize k8s/base

# Deploy using base configuration
kubectl apply -k k8s/base

# Or deploy using production overlay
kubectl apply -k k8s/overlays/production

# Check deployment status
kubectl get pods -n unmute -w

# Check init container logs (model download from S3)
kubectl logs -n unmute <pod-name> -c model-sync

# Check LLM container logs
kubectl logs -n unmute <pod-name> -c llm
```

Alternative: Deploy without Kustomize (using raw manifests in `k8s/base/`):

```bash
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/model-downloader-sa.yaml
kubectl apply -f k8s/base/llm-deployment.yaml
```

**Note:** The base configuration uses placeholder values like `$(AWS_ACCOUNT_ID)`. These are only replaced when using Kustomize. If deploying raw manifests, you must manually edit the files first.

### 5. Expose and Access the LLM API

The deployment creates an internal ClusterIP service. To access it externally, create a LoadBalancer:

```bash
# Create LoadBalancer service to expose the LLM API
kubectl expose deployment llm -n unmute \
  --type=LoadBalancer \
  --name=llm-external \
  --port=8000 \
  --target-port=8000

# Wait for LoadBalancer to be provisioned
kubectl get svc llm-external -n unmute -w

# Get the LoadBalancer URL
export LLM_URL=$(kubectl get svc llm-external -n unmute -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "LLM API URL: http://${LLM_URL}:8000"

# Test the API - List available models
curl http://${LLM_URL}:8000/v1/models

# Test chat completion
curl http://${LLM_URL}:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "messages": [
      {"role": "user", "content": "Hello! Can you explain what you are?"}
    ],
    "max_tokens": 100
  }'
```

Alternative: Use port-forwarding for local testing:

```bash
# Forward local port 8000 to the LLM service
kubectl port-forward -n unmute svc/llm 8000:8000

# In another terminal, test the API
curl http://localhost:8000/v1/models
```

### API Endpoints

The vLLM service exposes an OpenAI-compatible API:

- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Chat completion
- `POST /v1/completions` - Text completion
- `GET /health` - Health check

## Configuration

All configuration is managed through Kustomize using a single configuration file.

### Configuration File

Edit `k8s/config/default-config.env` to customize your deployment:

| Variable                  | Description                                      | Default                              |
| ------------------------- | ------------------------------------------------ | ------------------------------------ |
| `AWS_ACCOUNT_ID`          | Your AWS account ID                              | `676164205626`                       |
| `AWS_REGION`              | AWS region                                       | `us-east-1`                          |
| `S3_BUCKET_NAME`          | S3 bucket name for model storage                | `llm-models`                         |
| `MODEL_REPO`              | HuggingFace model repository                    | `meta-llama/Meta-Llama-3.1-8B-Instruct` |
| `MODEL_MAX_LENGTH`        | Maximum context length                          | `8192`                               |
| `VLLM_IMAGE`              | vLLM container image                            | `vllm/vllm-openai:v0.11.0`          |
| `LLM_MEMORY_LIMIT`        | Memory limit for LLM container                  | `24Gi`                               |
| `LLM_MEMORY_REQUEST`      | Memory request for LLM container                | `12Gi`                               |
| `INSTANCE_TYPE`           | EC2 instance type for GPU nodes                 | `g6e.xlarge`                         |
| `IAM_ROLE_NAME`           | IAM role name for S3 access                     | `deepfake-pytorch-eks-model-downloader` |
| `HUGGING_FACE_HUB_TOKEN`  | HuggingFace API token                           | `hf_your_token_here`                 |

See [`k8s/config/default-config.env.example`](k8s/config/default-config.env.example) for all available options.

### AWS Account Setup

```bash
# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# After EKS cluster creation, get OIDC provider for IRSA
aws eks describe-cluster --name YOUR_CLUSTER_NAME \
  --query "cluster.identity.oidc.issuer" --output text
```

## Project Structure

```text
llama_3_1_8b/
├── k8s/                           # Kubernetes manifests
│   ├── base/                      # Base Kustomize configuration
│   │   ├── kustomization.yaml     # Kustomize config
│   │   ├── namespace.yaml         # Namespace and secrets
│   │   ├── model-downloader-sa.yaml # ServiceAccount + download scripts
│   │   └── llm-deployment.yaml    # LLM deployment (vLLM)
│   ├── config/                    # Configuration management
│   │   ├── default-config.env     # Configuration values
│   │   └── default-config.env.example # Example config
│   ├── overlays/                  # Environment-specific overlays
│   │   └── production/            # Production overlay
│   │       ├── kustomization.yaml
│   │       └── config.env.example
│   ├── cluster.yaml               # EKS cluster definition (eksctl)
│   └── ingress.yaml               # Optional ALB Ingress
├── scripts/                       # Helper scripts
│   ├── upload-models-to-s3.sh     # Upload model to S3
│   ├── requirements.txt           # Python dependencies
│   └── README.md                  # Scripts documentation
└── README.md                      # This file
```

## Architecture

### Deployment Architecture

```text
API Client
    ↓
[LoadBalancer Service: llm-external:8000]
    ↓
┌────────────────────────────────────────┐
│ EKS Cluster                            │
│                                        │
│  GPU Node (g6e.xlarge)                │
│  ┌──────────────────────────────────┐ │
│  │ LLM Pod                          │ │
│  │  ┌────────────────────────────┐  │ │
│  │  │ Init Container (aws-cli)   │  │ │
│  │  │  - Downloads model from S3 │  │ │
│  │  │  - Caches to EmptyDir      │  │ │
│  │  └────────────────────────────┘  │ │
│  │  ┌────────────────────────────┐  │ │
│  │  │ vLLM Container             │  │ │
│  │  │  - Loads cached model      │  │ │
│  │  │  - Serves OpenAI API       │  │ │
│  │  │  - Port 8000               │  │ │
│  │  └────────────────────────────┘  │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
    ↓
[S3 Bucket: llm-models/llm/]
    (Model: Meta-Llama-3.1-8B-Instruct)
```

### Model Loading Flow

```text
1. Pod starts
    ↓
2. Init Container (aws-cli)
    ├─ Uses IRSA for S3 access (no keys needed)
    ├─ Downloads model from S3 (~16GB)
    └─ Caches to EmptyDir: /models/.cache/huggingface/hub/
    ↓
3. Main Container (vLLM)
    ├─ Finds pre-downloaded model in shared volume
    ├─ Loads model into GPU memory
    └─ Starts API server on port 8000
    ↓
4. Ready to serve requests (3-5 min total)
```

### Key Components

- **Init Container**: Downloads model from S3 using IRSA (IAM Roles for Service Accounts)
- **vLLM Container**: Runs the model inference engine with OpenAI-compatible API
- **EmptyDir Volume**: Shared ephemeral storage between init and main containers (20Gi)
- **GPU**: NVIDIA L40S (48GB VRAM) on g6e.xlarge instances
- **Model Cache**: HuggingFace format in `/models/.cache/huggingface/hub/`

## Troubleshooting

### Pod Not Starting

Check init container logs for S3 download issues:
```bash
kubectl logs -n unmute <pod-name> -c model-sync
```

Common issues:
- IRSA role not configured correctly
- S3 bucket doesn't exist or is in different region
- Model files not uploaded to S3

### Model Not Loading

Check vLLM container logs:
```bash
kubectl logs -n unmute <pod-name> -c llm
```

Common issues:
- Insufficient GPU memory (need 48GB VRAM for 8B model)
- Model path incorrect in deployment
- HuggingFace token not set correctly

### LoadBalancer Not Accessible

Check service status:
```bash
kubectl get svc llm-external -n unmute
kubectl describe svc llm-external -n unmute
```

Common issues:
- Security groups blocking traffic
- LoadBalancer not yet provisioned (can take 2-3 minutes)
- Wrong AWS region

## Technologies Used

- **vLLM**: High-performance LLM inference engine
- **Meta-Llama-3.1-8B-Instruct**: Large language model
- **Kubernetes/EKS**: Container orchestration
- **Kustomize**: Configuration management
- **AWS S3**: Model weight storage
- **IRSA**: IAM Roles for Service Accounts (secure S3 access)
- **NVIDIA GPU**: L40S (48GB VRAM) on g6e.xlarge instances

## Related Projects

- **vLLM**: <https://github.com/vllm-project/vllm>
- **Meta Llama**: <https://huggingface.co/meta-llama>
- **Kustomize**: <https://kustomize.io/>

## License

MIT License - see [LICENSE](LICENSE) for details.
