# Scripts

Utility scripts for the Unmute project.

## Setup

Create a virtual environment and install dependencies:

```bash
python -m pip install virtualenv --break-system-packages -Uq
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/requirements.txt -Uq
```

## Scripts

### upload-models-to-s3.sh

Downloads Meta-Llama-3.1-8B-Instruct model weights from HuggingFace Hub and uploads them to S3 for use with EKS deployments.

#### Prerequisites

- AWS CLI configured with appropriate credentials
- HuggingFace token with access to gated models (Llama license must be accepted on HuggingFace)
- ~20GB free disk space for temporary downloads
- Python virtual environment with `huggingface_hub` installed (see Setup above)

#### Usage

```bash
# Set your HuggingFace token
export HUGGING_FACE_HUB_TOKEN=your_token_here

# Upload LLM model (~16GB)
./scripts/upload-models-to-s3.sh all

# Or explicitly specify llm
./scripts/upload-models-to-s3.sh llm

# List current S3 bucket contents
./scripts/upload-models-to-s3.sh list
```

#### Environment Variables

| Variable                 | Required | Description                                            |
| ------------------------ | -------- | ------------------------------------------------------ |
| `HUGGING_FACE_HUB_TOKEN` | Yes      | HuggingFace API token                                  |
| `WORK_DIR`               | No       | Directory for downloads (default: `./model-downloads`) |
| `AWS_REGION`             | No       | AWS region (default: `us-east-1`)                      |

#### Models Uploaded

| Model                                   | S3 Path                      | Size  |
| --------------------------------------- | ---------------------------- | ----- |
| `meta-llama/Meta-Llama-3.1-8B-Instruct` | `s3://.../llm-models/llm/`   | ~16GB |

### audit-security-groups.sh

Audits AWS security groups for potential issues.

```bash
./scripts/audit-security-groups.sh
```
