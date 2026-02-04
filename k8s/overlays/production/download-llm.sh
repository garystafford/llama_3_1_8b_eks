#!/bin/bash
set -e

DOWNLOAD_DIR="/models/.cache/huggingface/hub"
MARKER_FILE="/models/.cache/.llm-download-complete"
# Hardcoded values from config
AWS_ACCOUNT_ID="676164205626"
AWS_REGION="us-east-1"
S3_BUCKET_NAME="audio-models"
MODEL_REPO="meta-llama/Meta-Llama-3.1-8B-Instruct"
MODEL_NAME="Meta-Llama-3.1-8B-Instruct"

S3_BUCKET="s3://${AWS_ACCOUNT_ID}-sagemaker-${AWS_REGION}/${S3_BUCKET_NAME}"
MODEL_DIR="models--meta-llama--Meta-Llama-3.1-8B-Instruct"

mkdir -p "${DOWNLOAD_DIR}/${MODEL_DIR}"

# Check if already downloaded
if [ -f "${MARKER_FILE}" ]; then
  echo "LLM models already cached, skipping download"
  ls -lh "${DOWNLOAD_DIR}/${MODEL_DIR}/" 2>/dev/null | head -5 || true
  exit 0
fi

echo "Downloading LLM models from S3..."
echo "Source: ${S3_BUCKET}/llm/"
echo "Destination: ${DOWNLOAD_DIR}/${MODEL_DIR}/"
echo "Model: ${MODEL_NAME}"

# Download LLM model files directly to model directory
aws s3 sync "${S3_BUCKET}/llm/" "${DOWNLOAD_DIR}/${MODEL_DIR}/" \
  --exclude ".cache/*" \
  --no-progress \
  --only-show-errors

# Verify download - check for config.json which should always be present
if [ -f "${DOWNLOAD_DIR}/${MODEL_DIR}/config.json" ]; then
  echo "LLM model download complete"
  touch "${MARKER_FILE}"
  ls -lh "${DOWNLOAD_DIR}/${MODEL_DIR}/" 2>/dev/null | head -10 || true
else
  echo "ERROR: LLM model download failed - config.json not found"
  exit 1
fi
