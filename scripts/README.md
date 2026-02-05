# Utility Scripts

Utility scripts for the analysis project.

## Setup

Create a virtual environment and install dependencies:

```bash
python -m pip install virtualenv --break-system-packages -Uq
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/requirements.txt -Uq
```

## Required Environment Variables

These are all the environment variables required for the scripts.

```bash
export HUGGING_FACE_HUB_TOKEN=<your_hf_token>
export S3_BUCKET=<your_s3_bucket_name>
```

## Scripts

### upload-models-to-s3.sh

Downloads Meta-Llama-3.1-8B-Instruct model weights from HuggingFace Hub and uploads them to S3 for use with EKS deployments.

#### Prerequisites

- AWS CLI configured with appropriate credentials
- HuggingFace token with access to gated models (Llama license must be accepted on HuggingFace)
- ~40GB free disk space for temporary downloads
- Python virtual environment with `huggingface_hub` installed (see Setup above)

#### Usage

```bash
# Set your HuggingFace token
export HUGGING_FACE_HUB_TOKEN=<your_hf_token>
export S3_BUCKET=<your_s3_bucket_name>

# Upload LLM model (~32GB)
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
| `meta-llama/Meta-Llama-3.1-8B-Instruct` | `s3://.../llm-models/llm/`   | ~32GB |

### test_llm_api.py

Comprehensive test suite for validating the deployed LLM API endpoints.

#### Usage

```bash
# Test via HTTPS custom domain
python scripts/test_llm_api.py --url https://analysis.creativitylabsai.com

# Test via LoadBalancer
python scripts/test_llm_api.py --url http://<loadbalancer-url>:8000

# Test via port-forward
kubectl port-forward -n analysis svc/llm 8000:8000 &
python scripts/test_llm_api.py
kill %1
```

#### Tests Performed

- Health endpoint check
- Model listing validation
- Chat completion with sample prompt
- Text completion with sample prompt

### prompt_llm.py

Interactive script to prompt the LLM with full control over all inference parameters.

#### Features

- **Two modes**: Text completion and chat completion
- **Full parameter control**: All vLLM inference parameters exposed
- **Multiple completions**: Generate and compare multiple outputs
- **Metadata display**: View token usage and generation statistics
- **JSON output**: Export raw responses for analysis

#### Basic Usage

```bash
# Simple text completion
python scripts/prompt_llm.py --url https://analysis.creativitylabsai.com \
  --prompt "The future of artificial intelligence is"

# Chat mode with system message
python scripts/prompt_llm.py --url https://analysis.creativitylabsai.com \
  --mode chat \
  --system "You are a helpful Python programming assistant" \
  --user-message "How do I sort a dictionary by value?"

# Show usage statistics
python scripts/prompt_llm.py --url https://analysis.creativitylabsai.com \
  --prompt "What is machine learning?" \
  --show-metadata
```

#### Advanced Parameters

**Sampling Control:**

```bash
# Creative generation (high temperature)
python scripts/prompt_llm.py \
  --prompt "Write a creative story about robots" \
  --temperature 0.9 \
  --top-p 0.95 \
  --max-tokens 500

# Deterministic output (low temperature)
python scripts/prompt_llm.py \
  --prompt "What is 2+2?" \
  --temperature 0.1 \
  --max-tokens 50

# Top-k sampling
python scripts/prompt_llm.py \
  --prompt "Complete this sentence: The best way to learn coding is" \
  --top-k 50 \
  --temperature 0.8
```

**Penalty Parameters:**

```bash
# Reduce repetition
python scripts/prompt_llm.py \
  --prompt "List creative AI applications:" \
  --frequency-penalty 0.5 \
  --repetition-penalty 1.2

# Encourage diverse topics
python scripts/prompt_llm.py \
  --prompt "Discuss the future of technology" \
  --presence-penalty 0.6 \
  --max-tokens 300
```

**Multiple Completions:**

```bash
# Generate 3 variations
python scripts/prompt_llm.py \
  --prompt "Write a tagline for an AI startup" \
  --n 3 \
  --max-tokens 20 \
  --temperature 0.9

# Beam search for best output
python scripts/prompt_llm.py \
  --prompt "Translate to French: Hello, how are you?" \
  --use-beam-search \
  --length-penalty 1.0
```

**Stop Sequences:**

```bash
# Stop at specific tokens
python scripts/prompt_llm.py \
  --prompt "List three programming languages:\n1." \
  --stop "\n4" "\n\n" \
  --max-tokens 100
```

#### Available Parameters

| Parameter              | Type    | Default | Description                                          |
| ---------------------- | ------- | ------- | ---------------------------------------------------- |
| `--url`                | string  | localhost:8000 | API endpoint URL                              |
| `--model`              | string  | Meta-Llama-3.1-8B-Instruct | Model identifier                  |
| `--mode`               | choice  | completion | Mode: `completion` or `chat`                      |
| `--prompt`             | string  | -       | Text prompt (completion mode)                        |
| `--system`             | string  | -       | System message (chat mode)                           |
| `--user-message`       | string  | -       | User message (chat mode)                             |
| `--max-tokens`         | int     | 512     | Maximum tokens to generate                           |
| `--min-tokens`         | int     | 0       | Minimum tokens to generate                           |
| `--temperature`        | float   | 0.7     | Sampling temperature (0.0-2.0)                       |
| `--top-p`              | float   | 1.0     | Nucleus sampling threshold (0.0-1.0)                 |
| `--top-k`              | int     | -1      | Top-k sampling (-1 to disable)                       |
| `--frequency-penalty`  | float   | 0.0     | Penalize frequent tokens (-2.0 to 2.0)               |
| `--presence-penalty`   | float   | 0.0     | Penalize present tokens (-2.0 to 2.0)                |
| `--repetition-penalty` | float   | 1.0     | Penalize repetitions (>1.0 = penalize)               |
| `--stop`               | list    | -       | Stop sequences                                       |
| `--n`                  | int     | 1       | Number of completions                                |
| `--best-of`            | int     | -       | Generate N, return best (completion only)            |
| `--use-beam-search`    | flag    | false   | Use beam search (completion only)                    |
| `--length-penalty`     | float   | 1.0     | Length penalty for beam search                       |
| `--echo`               | flag    | false   | Echo prompt in response (completion only)            |
| `--logprobs`           | int     | -       | Return log probabilities                             |
| `--show-metadata`      | flag    | false   | Show token usage and statistics                      |
| `--json`               | flag    | false   | Output raw JSON response                             |

#### Parameter Tuning Guidelines

**Temperature:**
- `0.0-0.3`: Deterministic, factual responses (technical documentation, math)
- `0.4-0.7`: Balanced creativity and coherence (general Q&A, code generation)
- `0.8-1.2`: Creative, diverse outputs (creative writing, brainstorming)
- `1.3-2.0`: Very creative, experimental (poetry, abstract ideas)

**Top-p (Nucleus Sampling):**
- `0.9-1.0`: Standard setting, allows diverse tokens
- `0.7-0.9`: More focused, filters unlikely tokens
- `0.5-0.7`: Conservative, high-probability tokens only

**Penalties:**
- `frequency_penalty > 0`: Reduce word repetition (technical writing)
- `presence_penalty > 0`: Encourage topic diversity (long-form content)
- `repetition_penalty > 1.0`: Penalize any repetition (creative content)
