#!/usr/bin/env python3
"""
OpenRouter Model Discovery & OCR Fallback Script

Discovers free and low-cost vision-capable models from OpenRouter
and creates a fallback chain for OCR tasks.

Usage:
    python3 scripts/list_vision_models.py [--refresh] [--test]
"""

import json
import time
import urllib.request
import base64
import os
import re
from pathlib import Path

OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not OR_KEY:
    # Try to load from .env
    for line in open(".env"):
        if line.startswith("OPENROUTER_API_KEY="):
            OR_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not OR_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment or .env")

URL = "https://openrouter.ai/api/v1"
HEAD = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}

TEST_IMAGE = "scans/roman-demeter-op1.jpeg"  # Use existing scan for testing


def get_free_models() -> list[dict]:
    """Get all free models from OpenRouter."""
    req = urllib.request.Request(f"{URL}/models", headers=HEAD)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())

    free_models = []
    for m in data.get("data", []):
        if ":free" not in m.get("id", "").lower():
            continue
        free_models.append({
            "id": m["id"],
            "context_length": m.get("context_length", 0),
            "price": 0,
        })
    return sorted(free_models, key=lambda x: x["id"])


def get_minimax_models() -> list[dict]:
    """Get all MiniMax models from OpenRouter, sorted by price."""
    req = urllib.request.Request(f"{URL}/models", headers=HEAD)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())

    minimax_models = []
    for m in data.get("data", []):
        mid = m["id"].lower()
        if "minimax" not in mid:
            continue
        price = float(m.get("pricing", {}).get("prompt", 0))
        minimax_models.append({
            "id": m["id"],
            "context_length": m.get("context_length", 0),
            "price": price,
            "free": price == 0,
        })
    return sorted(minimax_models, key=lambda x: (not x["free"], x["price"]))


def test_vision(model_id: str, image_b64: str, timeout: int = 60) -> dict | None:
    """
    Test if a model supports vision by sending a simple image+text request.

    Returns dict with keys: works, answer, cost, has_reasoning, error
    """
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": "Answer with only the surname."}
        ]}],
        "max_tokens": 100
    }

    req = urllib.request.Request(URL + "/chat/completions", data=json.dumps(payload).encode(), headers=HEAD)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())

        msg = resp["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning", "") or ""
        cost = resp.get("usage", {}).get("cost", 0)

        return {
            "works": True,
            "answer": content.strip()[:100],
            "cost": cost,
            "has_reasoning": bool(msg.get("reasoning")),
            "error": None
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200] if e.fp else ""
        return {
            "works": False,
            "answer": None,
            "cost": 0,
            "has_reasoning": False,
            "error": f"HTTP {e.code}: {body[:100]}"
        }
    except Exception as e:
        return {
            "works": False,
            "answer": None,
            "cost": 0,
            "has_reasoning": False,
            "error": str(e)[:100]
        }


def discover_vision_models(test_image: str) -> dict:
    """
    Discover all vision-capable models on OpenRouter.

    Returns dict with:
    - free_vision: list of free models that work with images
    - minimax_vision: list of MiniMax models (free first, then by price)
    """
    print("Fetching all free models from OpenRouter...")
    free_models = get_free_models()
    print(f"Found {len(free_models)} free models")

    print("Fetching all MiniMax models...")
    minimax_models = get_minimax_models()
    print(f"Found {len(minimax_models)} MiniMax models")

    if not os.path.exists(test_image):
        print(f"Warning: Test image {test_image} not found. Skipping vision tests.")
        return {
            "free_vision": [],
            "minimax_vision": minimax_models,
            "all_free_tested": free_models
        }

    print(f"Reading test image: {test_image}")
    with open(test_image, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    print("\n=== Testing free models for vision ===")
    free_vision = []
    for m in free_models:
        print(f"Testing {m['id']}...", end=" ", flush=True)
        result = test_vision(m["id"], image_b64)
        if result["works"] and "demeter" in result["answer"].lower():
            m.update(result)
            free_vision.append(m)
            print(f"✅ {result['answer'][:40]} (${result['cost']:.6f})")
        else:
            print(f"❌ {result['error'] or 'no demeter'}")
        time.sleep(0.5)  # Rate limiting

    print("\n=== Testing MiniMax models for vision ===")
    minimax_vision = []
    for m in minimax_models:
        print(f"Testing {m['id']}...", end=" ", flush=True)
        result = test_vision(m["id"], image_b64)
        if result["works"] and "demeter" in result["answer"].lower():
            m.update(result)
            minimax_vision.append(m)
            print(f"✅ {result['answer'][:40]} (${result['cost']:.6f})")
        else:
            print(f"❌ {result['error'] or 'no demeter'}")
        time.sleep(0.5)

    return {
        "free_vision": free_vision,
        "minimax_vision": minimax_vision,
        "all_free_tested": free_models
    }


def generate_fallback_chain(discovered: dict) -> list[dict]:
    """
    Generate a prioritized fallback chain for OCR.

    Priority:
    1. Free vision models (sorted by cost ascending)
    2. MiniMax low-cost paid models
    """
    chain = []

    # Add free models first
    for m in discovered.get("free_vision", []):
        chain.append({
            "model": m["id"],
            "type": "free",
            "cost_per_call": m["cost"],
            "has_reasoning": m.get("has_reasoning", False),
            "priority": 0
        })

    # Add MiniMax paid models (free first, then by price)
    for m in discovered.get("minimax_vision", []):
        if m["free"]:
            continue  # Already added
        chain.append({
            "model": m["id"],
            "type": "paid",
            "cost_per_call": m["cost"],
            "price_per_1m": m["price"] * 1_000_000,
            "has_reasoning": m.get("has_reasoning", False),
            "priority": len([x for x in chain if x["type"] == "free"]) + 1
        })

    return chain


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover vision-capable models on OpenRouter")
    parser.add_argument("--test", action="store_true", help="Run vision tests")
    parser.add_argument("--refresh", action="store_true", help="Refresh model list from API")
    parser.add_argument("--output", default="config/vision_models.json", help="Output file")
    parser.add_argument("--image", default=TEST_IMAGE, help="Test image path")
    args = parser.parse_args()

    cache_file = "config/vision_models_cache.json"

    if args.refresh or args.test:
        discovered = discover_vision_models(args.image)

        # Save cache
        with open(cache_file, "w") as f:
            json.dump(discovered, f, indent=2)
        print(f"\nSaved cache to {cache_file}")
    else:
        # Load from cache
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                discovered = json.load(f)
            print(f"Loaded cached model data from {cache_file}")
        else:
            print("No cache found. Use --refresh to fetch from API.")
            return

    # Generate fallback chain
    chain = generate_fallback_chain(discovered)

    print("\n" + "="*60)
    print("VISION-CAPABLE MODELS FALLBACK CHAIN")
    print("="*60)
    print("\nPriority | Model                                     | Type | Cost/call | Reasoning")
    print("-"*90)
    for i, m in enumerate(chain, 1):
        reasoning = "Yes" if m.get("has_reasoning") else "No"
        if m["type"] == "free":
            print(f"  {i:<6} | {m['model']:<40} | FREE | ${m['cost_per_call']:.6f} | {reasoning}")
        else:
            print(f"  {i:<6} | {m['model']:<40} | paid | ${m['cost_per_call']:.6f} | {reasoning}")

    # Save to config
    output = {
        "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fallback_chain": chain,
        "free_vision_models": discovered.get("free_vision", []),
        "minimax_vision_models": discovered.get("minimax_vision", [])
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved fallback chain to {args.output}")

    # Print OCR script template
    print("\n" + "="*60)
    print("OCR FALLBACK SCRIPT TEMPLATE")
    print("="*60)
    print("""
# Add to your OCR worker script:

VISION_MODELS = [
""")
    for m in chain:
        reasoning_note = " (reasoning)" if m.get("has_reasoning") else ""
        print(f'    "{m["model"]}",  # {"FREE" if m["type"] == "free" else "paid"}{reasoning_note}')
    print("""

def call_vision_ocr(image_b64: str, test_prompt: str = "Extract surname and given name as JSON.") -> dict:
    \"\"\"Call vision model with fallback chain. Handles reasoning models correctly.\"\"\"
    for model_id in VISION_MODELS:
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": test_prompt}
            ]}],
            "max_tokens": 500
        }
        req = urllib.request.Request(URL + "/chat/completions", data=json.dumps(payload).encode(), headers=HEAD)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode())
            msg = resp["choices"][0]["message"]
            # Handle both content and reasoning fields
            content = msg.get("content") or msg.get("reasoning", "") or ""
            return {"works": True, "model": model_id, "content": content.strip()}
        except Exception:
            continue
    return {"works": False}
""")


if __name__ == "__main__":
    main()
