#!/usr/bin/env python3
"""
Interactive LLM prompting script with full inference parameter control.

This script provides a simple interface to prompt the LLM with full control
over all inference parameters supported by vLLM's OpenAI-compatible API.

Setup:
    pip install requests

Usage:
    # Basic usage with default parameters
    python scripts/prompt_llm.py --url https://analysis.creativitylabsai.com \
        --prompt "What is the capital of France?"

    # Chat mode with conversation
    python scripts/prompt_llm.py --url https://analysis.creativitylabsai.com \
        --mode chat \
        --prompt "You are a helpful assistant" \
        --user-message "Explain quantum computing in simple terms"

    # Advanced parameters for creative generation
    python scripts/prompt_llm.py --url https://analysis.creativitylabsai.com \
        --prompt "Write a short poem about AI" \
        --max-tokens 200 \
        --temperature 0.9 \
        --top-p 0.95 \
        --frequency-penalty 0.5 \
        --presence-penalty 0.3

    # Via LoadBalancer (requires whitelisted IP)
    python scripts/prompt_llm.py \
        --url http://k8s-analysis-llmexter-....elb.us-east-1.amazonaws.com:8000 \
        --prompt "Hello, world!"

    # Via port-forward
    kubectl port-forward -n analysis svc/llm 8000:8000 &
    python scripts/prompt_llm.py --prompt "Test prompt"
    kill %1
"""

import argparse
import sys
import requests
import json
import time
from typing import Optional, List, Tuple


def prompt_completion(
    base_url: str,
    model_name: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 1.0,
    top_k: int = -1,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    repetition_penalty: float = 1.0,
    stop: Optional[List[str]] = None,
    stream: bool = False,
    n: int = 1,
    best_of: Optional[int] = None,
    logprobs: Optional[int] = None,
    echo: bool = False,
    min_tokens: int = 0,
    use_beam_search: bool = False,
    length_penalty: float = 1.0,
) -> Tuple[dict, float]:
    """
    Send a text completion request with full parameter control.

    Parameters:
        base_url: Base URL of the LLM API
        model_name: Model identifier
        prompt: Text prompt to complete
        max_tokens: Maximum tokens to generate (default: 512)
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
            Lower = more focused/deterministic, Higher = more creative/random
        top_p: Nucleus sampling threshold 0.0-1.0 (default: 1.0)
            Only consider tokens with cumulative probability >= top_p
        top_k: Top-k sampling - only consider top k tokens (default: -1 = disabled)
        frequency_penalty: Penalize tokens based on frequency -2.0 to 2.0 (default: 0.0)
            Positive values decrease likelihood of repeating tokens
        presence_penalty: Penalize tokens that have appeared -2.0 to 2.0 (default: 0.0)
            Positive values encourage new topics
        repetition_penalty: Penalize repetitions (default: 1.0)
            >1.0 = penalize, <1.0 = encourage repetition
        stop: List of stop sequences (default: None)
        stream: Stream response tokens (default: False)
        n: Number of completions to generate (default: 1)
        best_of: Generate best_of completions, return best n (default: None)
        logprobs: Return log probabilities (default: None)
        echo: Echo the prompt in response (default: False)
        min_tokens: Minimum tokens to generate (default: 0)
        use_beam_search: Use beam search instead of sampling (default: False)
        length_penalty: Length penalty for beam search (default: 1.0)
    """
    payload = {
        "model": model_name,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "stream": stream,
        "n": n,
        "echo": echo,
    }

    # Add optional parameters only if non-default
    if top_k > 0:
        payload["top_k"] = top_k
    if repetition_penalty != 1.0:
        payload["repetition_penalty"] = repetition_penalty
    if stop:
        payload["stop"] = stop
    if best_of:
        payload["best_of"] = best_of
    if logprobs:
        payload["logprobs"] = logprobs
    if min_tokens > 0:
        payload["min_tokens"] = min_tokens
    if use_beam_search:
        payload["use_beam_search"] = use_beam_search
        payload["length_penalty"] = length_penalty

    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        elapsed_time = time.time() - start_time
        response.raise_for_status()
        return response.json(), elapsed_time
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def prompt_chat(
    base_url: str,
    model_name: str,
    system_message: Optional[str],
    user_message: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 1.0,
    top_k: int = -1,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    repetition_penalty: float = 1.0,
    stop: Optional[List[str]] = None,
    stream: bool = False,
    n: int = 1,
    logprobs: Optional[int] = None,
) -> Tuple[dict, float]:
    """
    Send a chat completion request with full parameter control.

    Parameters: Same as prompt_completion, plus:
        system_message: Optional system message to set assistant behavior
        user_message: User's message/question
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "stream": stream,
        "n": n,
    }

    # Add optional parameters only if non-default
    if top_k > 0:
        payload["top_k"] = top_k
    if repetition_penalty != 1.0:
        payload["repetition_penalty"] = repetition_penalty
    if stop:
        payload["stop"] = stop
    if logprobs:
        payload["logprobs"] = logprobs

    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        elapsed_time = time.time() - start_time
        response.raise_for_status()
        return response.json(), elapsed_time
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def print_response(
    response: dict, mode: str, elapsed_time: float, show_metadata: bool = False
):
    """Pretty print the response."""
    if mode == "chat":
        if "choices" in response and len(response["choices"]) > 0:
            for i, choice in enumerate(response["choices"]):
                content = choice["message"]["content"]
                if len(response["choices"]) > 1:
                    print(f"\n{'='*60}")
                    print(f"Completion {i+1}:")
                    print(f"{'='*60}")
                print(content)

                if show_metadata:
                    print(f"\n{'─'*60}")
                    print(f"Finish reason: {choice.get('finish_reason', 'N/A')}")
                    if "logprobs" in choice and choice["logprobs"]:
                        print(f"Logprobs available: Yes")
        else:
            print("❌ No response generated")
    else:  # completion mode
        if "choices" in response and len(response["choices"]) > 0:
            for i, choice in enumerate(response["choices"]):
                text = choice["text"]
                if len(response["choices"]) > 1:
                    print(f"\n{'='*60}")
                    print(f"Completion {i+1}:")
                    print(f"{'='*60}")
                print(text)

                if show_metadata:
                    print(f"\n{'─'*60}")
                    print(f"Finish reason: {choice.get('finish_reason', 'N/A')}")
                    if "logprobs" in choice and choice["logprobs"]:
                        print(f"Logprobs available: Yes")
        else:
            print("❌ No response generated")

    if show_metadata:
        print(f"\n{'─'*60}")
        print("Performance Metrics:")
        print(f"  Request latency: {elapsed_time:.3f}s")

        if "usage" in response:
            completion_tokens = response['usage'].get('completion_tokens', 0)
            if completion_tokens > 0 and elapsed_time > 0:
                tokens_per_sec = completion_tokens / elapsed_time
                print(f"  Tokens per second: {tokens_per_sec:.2f}")

        if "usage" in response:
            print(f"\n{'─'*60}")
            print("Usage Statistics:")
            print(f"  Prompt tokens: {response['usage'].get('prompt_tokens', 'N/A')}")
            print(f"  Completion tokens: {response['usage'].get('completion_tokens', 'N/A')}")
            print(f"  Total tokens: {response['usage'].get('total_tokens', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description="Prompt the LLM with full inference parameter control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic text completion
  %(prog)s --prompt "The future of AI is"

  # Chat mode with system message
  %(prog)s --mode chat --system "You are a Python expert" \\
      --user-message "How do I use list comprehensions?"

  # Creative generation with high temperature
  %(prog)s --prompt "Write a haiku about clouds" \\
      --temperature 0.9 --max-tokens 100

  # Deterministic output with low temperature
  %(prog)s --prompt "What is 2+2?" --temperature 0.1

  # Multiple completions
  %(prog)s --prompt "Complete this: Once upon a time" \\
      --n 3 --max-tokens 50
        """,
    )

    # Connection settings
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the LLM API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--model",
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        help="Model name (default: meta-llama/Meta-Llama-3.1-8B-Instruct)",
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["completion", "chat"],
        default="completion",
        help="API mode: completion (text) or chat (default: completion)",
    )

    # Prompt/message arguments
    parser.add_argument(
        "--prompt",
        help="Text prompt for completion mode (required for completion mode)",
    )
    parser.add_argument(
        "--system",
        help="System message for chat mode (optional)",
    )
    parser.add_argument(
        "--user-message",
        help="User message for chat mode (required for chat mode)",
    )

    # Generation parameters
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate (default: 512)",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=0,
        help="Minimum tokens to generate (default: 0)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature 0.0-2.0 (default: 0.7). Lower=deterministic, Higher=creative",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Nucleus sampling threshold 0.0-1.0 (default: 1.0)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=-1,
        help="Top-k sampling, -1 to disable (default: -1)",
    )
    parser.add_argument(
        "--frequency-penalty",
        type=float,
        default=0.0,
        help="Frequency penalty -2.0 to 2.0 (default: 0.0). Penalize token frequency",
    )
    parser.add_argument(
        "--presence-penalty",
        type=float,
        default=0.0,
        help="Presence penalty -2.0 to 2.0 (default: 0.0). Encourage new topics",
    )
    parser.add_argument(
        "--repetition-penalty",
        type=float,
        default=1.0,
        help="Repetition penalty (default: 1.0). >1.0 penalizes repetition",
    )
    parser.add_argument(
        "--stop",
        nargs="+",
        help="Stop sequences (space-separated list)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of completions to generate (default: 1)",
    )
    parser.add_argument(
        "--best-of",
        type=int,
        help="Generate best_of completions, return best n (completion mode only)",
    )
    parser.add_argument(
        "--use-beam-search",
        action="store_true",
        help="Use beam search instead of sampling (completion mode only)",
    )
    parser.add_argument(
        "--length-penalty",
        type=float,
        default=1.0,
        help="Length penalty for beam search (default: 1.0)",
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Echo the prompt in response (completion mode only)",
    )
    parser.add_argument(
        "--logprobs",
        type=int,
        help="Return top N log probabilities per token",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream response (not implemented in this script)",
    )

    # Output options
    parser.add_argument(
        "--show-metadata",
        action="store_true",
        help="Show response metadata (tokens used, finish reason, etc.)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.mode == "completion" and not args.prompt:
        parser.error("--prompt is required for completion mode")
    if args.mode == "chat" and not args.user_message:
        parser.error("--user-message is required for chat mode")

    if args.stream:
        print("⚠️  Warning: Streaming is not implemented in this script")
        args.stream = False

    # Display configuration
    if not args.json:
        print(f"\n{'='*60}")
        print(f"🤖 LLM Prompt - {args.mode.upper()} Mode")
        print(f"{'='*60}")
        print(f"URL: {args.url}")
        print(f"Model: {args.model}")
        print(f"Max tokens: {args.max_tokens}")
        print(f"Temperature: {args.temperature}")
        print(f"Top-p: {args.top_p}")
        if args.top_k > 0:
            print(f"Top-k: {args.top_k}")
        if args.frequency_penalty != 0.0:
            print(f"Frequency penalty: {args.frequency_penalty}")
        if args.presence_penalty != 0.0:
            print(f"Presence penalty: {args.presence_penalty}")
        if args.repetition_penalty != 1.0:
            print(f"Repetition penalty: {args.repetition_penalty}")
        if args.stop:
            print(f"Stop sequences: {args.stop}")
        if args.n > 1:
            print(f"Completions: {args.n}")
        print(f"{'='*60}\n")

    # Make request
    if args.mode == "chat":
        if not args.json:
            if args.system:
                print(f"System: {args.system}")
            print(f"User: {args.user_message}\n")
            print(f"{'─'*60}")
            print("Assistant:")

        response, elapsed_time = prompt_chat(
            base_url=args.url,
            model_name=args.model,
            system_message=args.system,
            user_message=args.user_message,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            frequency_penalty=args.frequency_penalty,
            presence_penalty=args.presence_penalty,
            repetition_penalty=args.repetition_penalty,
            stop=args.stop,
            stream=args.stream,
            n=args.n,
            logprobs=args.logprobs,
        )
    else:  # completion mode
        if not args.json:
            print(f"Prompt: {args.prompt}\n")
            print(f"{'─'*60}")
            print("Response:")

        response, elapsed_time = prompt_completion(
            base_url=args.url,
            model_name=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            frequency_penalty=args.frequency_penalty,
            presence_penalty=args.presence_penalty,
            repetition_penalty=args.repetition_penalty,
            stop=args.stop,
            stream=args.stream,
            n=args.n,
            best_of=args.best_of,
            logprobs=args.logprobs,
            echo=args.echo,
            min_tokens=args.min_tokens,
            use_beam_search=args.use_beam_search,
            length_penalty=args.length_penalty,
        )

    # Display response
    if args.json:
        # Add timing metadata to JSON output
        response_with_timing = response.copy()
        response_with_timing["_timing"] = {
            "request_latency_seconds": round(elapsed_time, 3),
            "tokens_per_second": (
                round(response.get("usage", {}).get("completion_tokens", 0) / elapsed_time, 2)
                if elapsed_time > 0 and response.get("usage", {}).get("completion_tokens", 0) > 0
                else None
            )
        }
        print(json.dumps(response_with_timing, indent=2))
    else:
        print_response(response, args.mode, elapsed_time, args.show_metadata)
        print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
