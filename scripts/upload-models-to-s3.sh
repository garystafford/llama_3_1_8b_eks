#!/bin/bash
# Upload LLM Model Weights to S3
#
# This script uploads the Meta-Llama-3.1-8B-Instruct model from your local HuggingFace
# cache (or downloads it first if not cached) to S3 for use with EKS deployment
# init containers.
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Python virtual environment with huggingface_hub installed
#   - HuggingFace token with access to gated models (Meta-Llama requires license acceptance)
#
# Setup:
#   python -m pip install virtualenv --break-system-packages -Uq
#   python -m venv .venv
#   source .venv/bin/activate
#   python -m pip install -r scripts/requirements.txt -Uq
#
# Usage:
#   export HUGGING_FACE_HUB_TOKEN=your_token
#   ./scripts/upload-models-to-s3.sh all

set -e

# Configuration
S3_BUCKET="s3://676164205626-sagemaker-us-east-1/llm-models"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}/hub"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Minimum sizes (in KB) to consider a model "fully downloaded"
MIN_SIZE_LLM=1000000 # ~1GB

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
	echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
	echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
	echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
	log_info "Checking prerequisites..."

	if ! command -v aws &>/dev/null; then
		log_error "AWS CLI not found. Install with: brew install awscli"
		exit 1
	fi

	if ! command -v python &>/dev/null; then
		log_error "Python not found"
		exit 1
	fi

	# Check huggingface_hub is installed
	if ! python -c "import huggingface_hub" 2>/dev/null; then
		log_error "huggingface_hub not installed"
		log_error "Run: pip install huggingface_hub"
		exit 1
	fi

	if [ -z "$HUGGING_FACE_HUB_TOKEN" ]; then
		log_error "HUGGING_FACE_HUB_TOKEN environment variable not set"
		log_error "Export your token: export HUGGING_FACE_HUB_TOKEN=hf_xxx"
		exit 1
	fi

	# Check AWS credentials
	if ! aws sts get-caller-identity &>/dev/null; then
		log_error "AWS credentials not configured or invalid"
		exit 1
	fi

	log_info "HuggingFace cache: ${HF_CACHE}"
	log_info "All prerequisites met"
}

# Get size of a directory in KB
get_dir_size_kb() {
	local dir="$1"
	if [ -d "$dir" ]; then
		du -sk "$dir" 2>/dev/null | cut -f1
	else
		echo "0"
	fi
}

# Check if model is cached and fully downloaded
is_model_cached() {
	local cache_dir="$1"
	local min_size="$2"
	local actual_size

	if [ ! -d "$cache_dir" ]; then
		return 1
	fi

	actual_size=$(get_dir_size_kb "$cache_dir")
	if [ "$actual_size" -ge "$min_size" ]; then
		return 0
	else
		return 1
	fi
}

# Download model using Python huggingface_hub
download_model() {
	local repo_id="$1"
	local force="${2:-False}"

	log_info "Downloading ${repo_id}..."

	python <<EOF
from huggingface_hub import snapshot_download
import os

snapshot_download(
    repo_id="${repo_id}",
    token=os.environ.get("HUGGING_FACE_HUB_TOKEN"),
    force_download=${force}
)
print("Download complete: ${repo_id}")
EOF
}

# Update model - force re-download to get latest
update_model() {
	local repo_id="$1"
	log_info "Updating ${repo_id} (forcing fresh download)..."
	download_model "$repo_id" "True"
}

# Get the snapshot directory for a cached model
get_snapshot_dir() {
	local cache_dir="$1"
	local snapshots_dir="${cache_dir}/snapshots"

	if [ -d "$snapshots_dir" ]; then
		# Get the first (usually only) snapshot directory
		local snapshot=$(ls -1 "$snapshots_dir" 2>/dev/null | head -1)
		if [ -n "$snapshot" ]; then
			echo "${snapshots_dir}/${snapshot}"
			return 0
		fi
	fi
	return 1
}

ensure_llm() {
	local cache_dir="${HF_CACHE}/models--meta-llama--Meta-Llama-3.1-8B-Instruct"

	if is_model_cached "$cache_dir" "$MIN_SIZE_LLM"; then
		log_info "LLM model found in cache ($(get_dir_size_kb "$cache_dir")KB)"
	else
		log_warn "LLM model not fully cached, downloading..."
		log_warn "This model requires accepting the Llama license on HuggingFace"
		download_model "meta-llama/Meta-Llama-3.1-8B-Instruct"
	fi
}

upload_llm() {
	local cache_dir="${HF_CACHE}/models--meta-llama--Meta-Llama-3.1-8B-Instruct"
	local snapshot_dir

	snapshot_dir=$(get_snapshot_dir "$cache_dir")
	if [ -z "$snapshot_dir" ]; then
		log_error "Could not find LLM model snapshot directory"
		exit 1
	fi

	log_info "Uploading LLM model from ${snapshot_dir}..."
	aws s3 sync "${snapshot_dir}/" "${S3_BUCKET}/llm/" \
		--region "$AWS_REGION"
	log_info "LLM model uploaded to ${S3_BUCKET}/llm/"
}

show_cache_status() {
	log_info "Local HuggingFace cache status:"
	echo ""

	local model="meta-llama--Meta-Llama-3.1-8B-Instruct"
	local cache_dir="${HF_CACHE}/models--${model}"
	local size=$(get_dir_size_kb "$cache_dir")
	local status

	if [ "$size" -ge "$MIN_SIZE_LLM" ]; then
		status="${GREEN}READY${NC}"
	elif [ "$size" -gt 0 ]; then
		status="${YELLOW}PARTIAL${NC}"
	else
		status="${RED}MISSING${NC}"
	fi

	printf "  %-45s %10s KB  [%b]\n" "$model" "$size" "$status"
	echo ""
}

show_s3_contents() {
	log_info "S3 bucket contents:"
	aws s3 ls "${S3_BUCKET}/" --recursive --human-readable --summarize
}

usage() {
	echo "Usage: $0 [llm|all|update|status|list]"
	echo ""
	echo "Commands:"
	echo "  llm     Ensure LLM model cached, then upload to S3"
	echo "  all     Ensure LLM model cached, then upload to S3 (default)"
	echo "  update  Force re-download LLM model to get latest version, then upload"
	echo "  status  Show local cache status"
	echo "  list    List current S3 bucket contents"
	echo ""
	echo "Environment variables:"
	echo "  HUGGING_FACE_HUB_TOKEN  Required: HuggingFace API token"
	echo "  HF_HOME                 Optional: HuggingFace home directory"
	echo "  AWS_REGION              Optional: AWS region (default: us-east-1)"
}

main() {
	local command="${1:-all}"

	case "$command" in
	llm)
		check_prerequisites
		ensure_llm
		upload_llm
		;;
	all)
		check_prerequisites
		show_cache_status
		log_info "Ensuring LLM model is cached..."
		ensure_llm
		log_info "Uploading LLM model to S3..."
		upload_llm
		show_s3_contents
		;;
	update)
		check_prerequisites
		log_info "Forcing fresh download of LLM model..."
		update_model "meta-llama/Meta-Llama-3.1-8B-Instruct"
		log_info "Uploading LLM model to S3..."
		upload_llm
		show_s3_contents
		;;
	status)
		show_cache_status
		;;
	list)
		show_s3_contents
		;;
	-h | --help | help)
		usage
		;;
	*)
		log_error "Unknown command: $command"
		usage
		exit 1
		;;
	esac

	log_info "Done!"
}

main "$@"
