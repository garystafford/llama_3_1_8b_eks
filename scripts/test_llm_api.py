#!/usr/bin/env python3
"""
Test script for LLM API deployed on EKS

Setup:
    pip install requests
    # Or in venv: source .venv/bin/activate && pip install requests

Usage:
    # Test via LoadBalancer (requires whitelisted IP)
    python scripts/test_llm_api.py --url http://k8s-analysis-llmexter-41bfdaa4a4-02e3cb8b5d974b29.elb.us-east-1.amazonaws.com:8000

    # Test via port-forward (run: kubectl port-forward -n analysis svc/llm 8000:8000)
    python scripts/test_llm_api.py --url http://localhost:8000

    # Run in background with port-forward
    kubectl port-forward -n analysis svc/llm 8000:8000 &
    python scripts/test_llm_api.py
    kill %1
"""

import argparse
import sys
import requests
import json


def test_health(base_url: str) -> bool:
    """Test the health endpoint"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        response.raise_for_status()
        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_list_models(base_url: str) -> bool:
    """Test the models listing endpoint"""
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        response.raise_for_status()
        data = response.json()

        if "data" in data and len(data["data"]) > 0:
            model_id = data["data"][0]["id"]
            print(f"✅ Models endpoint working - found model: {model_id}")
            return True
        else:
            print("❌ No models found in response")
            return False
    except Exception as e:
        print(f"❌ List models failed: {e}")
        return False


def test_chat_completion(base_url: str, model_name: str) -> bool:
    """Test the chat completion endpoint"""
    try:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "What is 2+2? Answer in one short sentence."}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            print(f"✅ Chat completion working")
            print(f"   Response: {content}")
            return True
        else:
            print("❌ No choices in response")
            return False
    except Exception as e:
        print(f"❌ Chat completion failed: {e}")
        return False


def test_text_completion(base_url: str, model_name: str) -> bool:
    """Test the text completion endpoint"""
    try:
        payload = {
            "model": model_name,
            "prompt": "The capital of France is",
            "max_tokens": 10,
            "temperature": 0.1
        }

        response = requests.post(
            f"{base_url}/v1/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            text = data["choices"][0]["text"]
            print(f"✅ Text completion working")
            print(f"   Response: {text}")
            return True
        else:
            print("❌ No choices in response")
            return False
    except Exception as e:
        print(f"❌ Text completion failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test LLM API endpoints")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the LLM API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--model",
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        help="Model name to use for completions"
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip health check"
    )

    args = parser.parse_args()

    print(f"\n🧪 Testing LLM API at: {args.url}\n")

    results = []

    # Test health endpoint
    if not args.skip_health:
        results.append(("Health", test_health(args.url)))

    # Test models endpoint
    results.append(("List Models", test_list_models(args.url)))

    # Test chat completion
    results.append(("Chat Completion", test_chat_completion(args.url, args.model)))

    # Test text completion
    results.append(("Text Completion", test_text_completion(args.url, args.model)))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 50 + "\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
