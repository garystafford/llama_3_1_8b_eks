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

| Feature              | Description                                                 |
| -------------------- | ----------------------------------------------------------- |
| **Model**            | Meta-Llama-3.1-8B-Instruct (16GB model size)                |
| **Inference Engine** | vLLM v0.11.0 with OpenAI-compatible API                     |
| **Model Loading**    | S3 + init containers (3-5 min startup)                      |
| **GPU**              | g6e.xlarge (NVIDIA L40S, 48GB VRAM)                         |
| **Context Length**   | 8192 tokens (configurable)                                  |
| **Access Control**   | LoadBalancer with source IP restrictions                    |
| **IAM**              | IRSA (IAM Roles for Service Accounts) for keyless S3 access |

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

> **Warning: Model Size and Timing**
> - Meta-Llama-3.1-8B-Instruct is **~32GB** (not 16GB)
> - HuggingFace download: 15-30 minutes (depends on bandwidth)
> - S3 upload: 10-20 minutes (depends on bandwidth and region)
> - Ensure your `EMPTYDIR_SIZE` in config.env is at least **40Gi** (model size + buffer)
> - Total process can take 30-60 minutes

```bash
# Set up Python environment for model upload script
python -m venv .venv
source .venv/bin/activate
pip install pip -Uq
pip install -r scripts/requirements.txt

# Set your HuggingFace token (required - you must accept Llama license on HuggingFace first)
export HUGGING_FACE_HUB_TOKEN=<your_hf_token>
export S3_BUCKET=<your_s3_bucket_name>

# Upload model to S3 (~32GB download + upload)
./scripts/upload-models-to-s3.sh all
```

### 3. Configure Kustomize

The project uses Kustomize for configuration management. Update configuration values in one place:

```bash
# Copy the example config and customize it (1x)
cp k8s/config/default-config.env.example k8s/config/default-config.env

# Edit the config file with your values
# Required changes:
# - AWS_ACCOUNT_ID: Your AWS account ID
# - IAM_ROLE_NAME: Your IAM role name (if different)
# - HUGGING_FACE_HUB_TOKEN: Your HuggingFace token
vim k8s/config/default-config.env
```

### 4. Deploy to EKS

**Production Deployment** (recommended - includes external LoadBalancer):

```bash
# Configure production overlay
cp k8s/overlays/production/config.env.example k8s/overlays/production/config.env
vim k8s/overlays/production/config.env

# Update these values:
# - AWS_ACCOUNT_ID: Your AWS account ID
# - INSTANCE_TYPE: Your GPU instance type (e.g., g5.2xlarge, g6e.xlarge)
# - IAM_ROLE_NAME: Your IAM role for S3 access

# Preview what will be deployed
kubectl kustomize k8s/overlays/production

# Deploy to production
kubectl apply -k k8s/overlays/production

# Expected resources created:
# - Namespace: analysis
# - ServiceAccount: model-downloader (with IRSA)
# - ConfigMaps: llm-config, model-download-script
# - Deployment: llm (1 replica)
# - Service: llm (ClusterIP - internal)
# - Service: llm-external (LoadBalancer - external with IP whitelist)

# Monitor deployment
kubectl get pods -n analysis -w
```

> **Deployment Timing Expectations**
>
> The pod initialization involves multiple stages:
> 1. **Pending** (0-30s): Waiting for GPU node scheduling
> 2. **Init:0/1** (2-5 min): Downloading 32GB model from S3 to EmptyDir volume
> 3. **PodInitializing** (10-30s): Init container completing
> 4. **Running** (1-3 min): vLLM loading 32GB model into GPU memory
> 5. **Ready** (60s): Readiness probe waiting for API to be fully responsive
>
> **Total time from apply to ready: 5-10 minutes**
>
> Monitor init container logs to see S3 download progress:
> ```bash
> POD_NAME=$(kubectl get pods -n analysis -l app=llm -o jsonpath='{.items[0].metadata.name}')
> kubectl logs -n analysis $POD_NAME -c model-sync -f
> ```

**Development Deployment** (base configuration):

```bash
# Deploy using base configuration (no LoadBalancer)
kubectl apply -k k8s/base

# Check deployment status
kubectl get pods -n analysis -w

# Check init container logs (model download from S3)
kubectl logs -n analysis <pod-name> -c model-sync

# Check LLM container logs
kubectl logs -n analysis <pod-name> -c llm
```

Alternative: Deploy without Kustomize (using raw manifests in `k8s/base/`):

```bash
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/model-downloader-sa.yaml
kubectl apply -f k8s/base/llm-deployment.yaml
```

**Note:** The base configuration uses placeholder values like `$(AWS_ACCOUNT_ID)`. These are only replaced when using Kustomize. If deploying raw manifests, you must manually edit the files first.

### 5. Access the LLM API

**Production (External LoadBalancer):**

The production overlay automatically creates an external LoadBalancer with IP whitelisting for security.

```bash
# Get the LoadBalancer URL
export LLM_URL=$(kubectl get svc llm-external -n analysis -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "LLM API URL: http://${LLM_URL}:8000"

# Test using Python script (comprehensive tests)
python scripts/test_llm_api.py --url http://${LLM_URL}:8000

# Or test manually
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

**Important:** The LoadBalancer has IP whitelisting enabled. Update `loadBalancerSourceRanges` in [k8s/overlays/production/llm-loadbalancer.yaml](k8s/overlays/production/llm-loadbalancer.yaml) with your current IP address.

**Development (Port-Forward):**

Use port-forwarding for local testing without exposing the service externally:

```bash
# Forward local port 8000 to the LLM service
kubectl port-forward -n analysis svc/llm 8000:8000 &

# Test with Python script
python scripts/test_llm_api.py

# Or test manually
curl http://localhost:8000/v1/models

# Kill port-forward when done
kill %1
```

### 6. Test the API

**Using Python Test Script** (recommended):

```bash
# Install dependencies
pip install requests
# Or: pip install -r scripts/requirements.txt

# Test via port-forward
kubectl port-forward -n analysis svc/llm 8000:8000 &
python scripts/test_llm_api.py
kill %1

# Test via LoadBalancer (if your IP is whitelisted)
python scripts/test_llm_api.py --url http://<loadbalancer-url>:8000
```

The test script validates:

- Health endpoint
- Model listing
- Chat completion
- Text completion

### API Endpoints

The vLLM service exposes an OpenAI-compatible API:

- `GET /health` - Health check
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Chat completion
- `POST /v1/completions` - Text completion

## Configuration

All configuration is managed through Kustomize using environment-specific configuration files.

### Production Overlay Configuration

Edit `k8s/overlays/production/config.env` for production deployment:

**Key Configuration Values:**

| Variable                | Description                      | Example Value                           |
| ----------------------- | -------------------------------- | --------------------------------------- |
| `AWS_ACCOUNT_ID`        | Your AWS account ID              | `676164205626`                          |
| `AWS_REGION`            | AWS region                       | `us-east-1`                             |
| `S3_BUCKET_NAME`        | S3 path prefix for models        | `audio-models`                          |
| `MODEL_REPO`            | HuggingFace model repository     | `meta-llama/Meta-Llama-3.1-8B-Instruct` |
| `MODEL_MAX_LENGTH`      | Maximum context length           | `8192`                                  |
| `MODEL_GPU_MEMORY_UTIL` | GPU memory utilization (0-1)     | `0.9` (21.6GB of 24GB)                  |
| `VLLM_IMAGE`            | vLLM container image             | `vllm/vllm-openai:v0.11.0`              |
| `LLM_MEMORY_LIMIT`      | Memory limit for LLM container   | `24Gi`                                  |
| `LLM_MEMORY_REQUEST`    | Memory request for LLM container | `12Gi`                                  |
| `EMPTYDIR_SIZE`         | EmptyDir volume for model cache  | `40Gi` (for 32GB model)                 |
| `INSTANCE_TYPE`         | EC2 instance type for GPU nodes  | `g5.2xlarge` or `g6e.xlarge`            |
| `IAM_ROLE_NAME`         | IAM role name for S3 access      | `deepfake-pytorch-eks-model-downloader` |
| `NAMESPACE`             | Kubernetes namespace             | `analysis`                              |

**Production-Specific Features:**

- **External LoadBalancer:** Automatic NLB provisioning for external access
- **IP Whitelisting:** Restricts access to specified IPs in `llm-loadbalancer.yaml`
- **Node Group Targeting:** Uses nodeSelector to place pods on specific GPU node groups
- **Optimized Download Script:** Custom S3 sync script with proper HuggingFace cache structure

See [`k8s/overlays/production/config.env.example`](k8s/overlays/production/config.env.example) for all available options.

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
│  GPU Node (g6e.xlarge)                 │
│  ┌──────────────────────────────────┐  │
│  │ LLM Pod                          │  │
│  │  ┌────────────────────────────┐  │  │
│  │  │ Init Container (aws-cli)   │  │  │
│  │  │  - Downloads model from S3 │  │  │
│  │  │  - Caches to EmptyDir      │  │  │
│  │  └────────────────────────────┘  │  │
│  │  ┌────────────────────────────┐  │  │
│  │  │ vLLM Container             │  │  │
│  │  │  - Loads cached model      │  │  │
│  │  │  - Serves OpenAI API       │  │  │
│  │  │  - Port 8000               │  │  │
│  │  └────────────────────────────┘  │  │
│  └──────────────────────────────────┘  │
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
kubectl logs -n analysis <pod-name> -c model-sync
```

Common issues:

- IRSA role not configured correctly
- S3 bucket doesn't exist or is in different region
- Model files not uploaded to S3

### Model Not Loading

Check vLLM container logs:

```bash
kubectl logs -n analysis <pod-name> -c llm
```

Common issues:

- Insufficient GPU memory (need 48GB VRAM for 8B model)
- Model path incorrect in deployment
- HuggingFace token not set correctly

### LoadBalancer Not Accessible

Check service status:

```bash
kubectl get svc llm-external -n analysis
kubectl describe svc llm-external -n analysis
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
