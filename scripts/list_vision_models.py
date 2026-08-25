#!/usr/bin/env python3
"""
Multi-Provider Vision Model Discovery & OCR Fallback Script

Discovers free and low-cost vision-capable models from:
- OpenRouter (primary, key in .env)
- Kilo Gateway (secondary, key in .env as KILO_API_KEY)

Usage:
    python3 scripts/list_vision_models.py --refresh --test
    python3 scripts/list_vision_models.py --openrouter-only
    python3 scripts/list_vision_models.py --kilo-only
"""

import json
import time
import urllib.request
import base64
import os
import re
from pathlib import Path
from typing import Optional

# Load API keys
def load_env_key(name: str, default: str = "") -> str:
    """Load key from .env file or environment."""
    if os.environ.get(name):
        return os.environ[name]
    for line in open(".env", errors="ignore"):
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return default

OR_KEY = load_env_key("OPENROUTER_API_KEY")
KILO_KEY = load_env_key("KILO_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1"
KILO_URL = "https://api.kilo.ai/api/gateway"

TEST_IMAGE = "scans/roman-demeter-op1.jpeg"


def get_openrouter_models() -> list[dict]:
    """Get all models from OpenRouter."""
    if not OR_KEY:
        print("Warning: OPENROUTER_API_KEY not found")
        return []

    HEAD = {"Authorization": f"Bearer {OR_KEY}"}
    req = urllib.request.Request(f"{OPENROUTER_URL}/models", headers=HEAD)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data.get("data", [])


def get_kilo_models() -> list[dict]:
    """Get all models from Kilo Gateway."""
    # Kilo gateway doesn't require auth for model listing
    req = urllib.request.Request(f"{KILO_URL}/models")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return data.get("data", [])
    except Exception as e:
        print(f"Kilo models error: {e}")
        return []


def extract_answer(msg: dict) -> tuple[str, bool]:
    """Extract text answer from message, checking both content and reasoning fields."""
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or ""
    # Some models put answer in reasoning, some in content
    combined = (content + " " + reasoning).lower()
    return content.strip() or reasoning.strip(), "demeter" in combined


def test_vision_openrouter(model_id: str, image_b64: str) -> dict:
    """Test vision capability on OpenRouter."""
    HEAD = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": "Answer with only the surname."}
        ]}],
        "max_tokens": 50
    }
    req = urllib.request.Request(
        f"{OPENROUTER_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers=HEAD
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
        msg = resp["choices"][0]["message"]
        answer_text, has_demeter = extract_answer(msg)
        cost = resp.get("usage", {}).get("cost", 0)
        return {
            "works": has_demeter,
            "answer": answer_text[:100],
            "cost": cost,
            "has_reasoning": bool(msg.get("reasoning")),
            "error": None
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200] if e.fp else ""
        return {"works": False, "answer": None, "cost": 0, "has_reasoning": False, "error": f"HTTP {e.code}: {body[:80]}"}
    except Exception as e:
        return {"works": False, "answer": None, "cost": 0, "has_reasoning": False, "error": str(e)[:80]}


def test_vision_kilo(model_id: str, image_b64: str) -> dict:
    """Test vision capability on Kilo Gateway."""
    if not KILO_KEY:
        return {"works": False, "answer": None, "cost": 0, "has_reasoning": False, "error": "No KILO_API_KEY"}

    HEAD = {"Authorization": f"Bearer {KILO_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": "Answer with only the surname."}
        ]}],
        "max_tokens": 50
    }
    req = urllib.request.Request(
        f"{KILO_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers=HEAD
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
        msg = resp["choices"][0]["message"]
        answer_text, has_demeter = extract_answer(msg)
        return {
            "works": has_demeter,
            "answer": answer_text[:100],
            "cost": resp.get("usage", {}).get("cost", 0),
            "has_reasoning": bool(msg.get("reasoning")),
            "error": None
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200] if e.fp else ""
        return {"works": False, "answer": None, "cost": 0, "has_reasoning": False, "error": f"HTTP {e.code}: {body[:80]}"}
    except Exception as e:
        return {"works": False, "answer": None, "cost": 0, "has_reasoning": False, "error": str(e)[:80]}


def discover_openrouter_vision(image_b64: str) -> dict:
    """Discover vision models on OpenRouter."""
    models = get_openrouter_models()
    free_models = [m for m in models if ":free" in m.get("id", "").lower()]
    minimax_models = [m for m in models if "minimax" in m.get("id", "").lower()]

    print(f"\n=== OpenRouter: Testing {len(free_models)} free + {len(minimax_models)} MiniMax models ===")

    results = {"free": [], "minimax": []}

    # Test free models
    for m in free_models:
        model_id = m["id"]
        print(f"  {model_id}...", end=" ", flush=True)
        result = test_vision_openrouter(model_id, image_b64)
        if result["works"]:
            results["free"].append({**m, **result})
            print(f"✅ ${result['cost']:.6f}")
        else:
            print(f"❌ {result['error'] or 'no match'}")
        time.sleep(0.3)

    # Test MiniMax models (free first, then paid)
    minimax_sorted = sorted(minimax_models, key=lambda x: float(x.get("pricing", {}).get("prompt", 1)))
    for m in minimax_sorted:
        model_id = m["id"]
        print(f"  {model_id}...", end=" ", flush=True)
        result = test_vision_openrouter(model_id, image_b64)
        if result["works"]:
            results["minimax"].append({**m, **result})
            print(f"✅ ${result['cost']:.6f}")
        else:
            print(f"❌ {result['error'] or 'no match'}")
        time.sleep(0.3)

    return results


def discover_kilo_vision(image_b64: str) -> dict:
    """Discover vision models on Kilo Gateway."""
    if not KILO_KEY:
        return {"models": [], "error": "No KILO_API_KEY"}

    models = get_kilo_models()
    print(f"\n=== Kilo Gateway: Testing {len(models)} models ===")

    results = []

    # Kilo uses provider/model format
    free_models = [m for m in models if ":free" in m.get("id", "").lower()]

    for m in free_models:
        model_id = m["id"]
        print(f"  {model_id}...", end=" ", flush=True)
        result = test_vision_kilo(model_id, image_b64)
        if result["works"]:
            results.append({**m, **result})
            print(f"✅ ${result['cost']:.6f}")
        else:
            print(f"❌ {result['error'] or 'no match'}")
        time.sleep(0.3)

    return {"models": results}


def build_fallback_chain(openrouter: dict, kilo: dict) -> list[dict]:
    """Build prioritized fallback chain from all providers."""
    chain = []

    # OpenRouter free vision models (by cost, free first)
    for m in sorted(openrouter.get("free", []), key=lambda x: x.get("cost", 0)):
        chain.append({
            "model": m["id"],
            "provider": "openrouter",
            "type": "free",
            "cost_per_call": m.get("cost", 0),
            "has_reasoning": m.get("has_reasoning", False),
        })

    # OpenRouter MiniMax paid (by price)
    for m in sorted(openrouter.get("minimax", []), key=lambda x: x.get("cost", 0)):
        if m.get("cost", 0) > 0:  # Skip free ones already added
            chain.append({
                "model": m["id"],
                "provider": "openrouter",
                "type": "paid",
                "cost_per_call": m.get("cost", 0),
                "has_reasoning": m.get("has_reasoning", False),
            })

    # Kilo free vision models
    for m in kilo.get("models", []):
        chain.append({
            "model": m["id"],
            "provider": "kilo",
            "type": "free",
            "cost_per_call": m.get("cost", 0),
            "has_reasoning": m.get("has_reasoning", False),
        })

    return chain


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover vision-capable models across providers")
    parser.add_argument("--refresh", action="store_true", help="Refresh from APIs")
    parser.add_argument("--test", action="store_true", help="Run vision tests")
    parser.add_argument("--openrouter-only", action="store_true", help="Only OpenRouter")
    parser.add_argument("--kilo-only", action="store_true", help="Only Kilo Gateway")
    parser.add_argument("--output", default="config/vision_models.json", help="Output file")
    parser.add_argument("--image", default=TEST_IMAGE, help="Test image path")
    args = parser.parse_args()

    cache_file = "config/vision_models_cache.json"

    if args.refresh or args.test:
        if not os.path.exists(args.image):
            print(f"Error: Test image {args.image} not found")
            return

        with open(args.image, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        openrouter_results = discover_openrouter_vision(image_b64) if not args.kilo_only else {"free": [], "minimax": []}
        kilo_results = discover_kilo_vision(image_b64) if not args.openrouter_only else {"models": []}

        discovered = {
            "openrouter": openrouter_results,
            "kilo": kilo_results,
            "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(cache_file, "w") as f:
            json.dump(discovered, f, indent=2)
        print(f"\nSaved cache to {cache_file}")
    else:
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                discovered = json.load(f)
            print(f"Loaded cache from {cache_file}")
        else:
            print("No cache. Use --refresh to fetch from APIs.")
            return

    chain = build_fallback_chain(
        discovered.get("openrouter", {}),
        discovered.get("kilo", {})
    )

    print("\n" + "="*80)
    print("VISION MODEL FALLBACK CHAIN")
    print("="*80)
    print(f"\n{'#':<4} {'Model':<55} {'Provider':<12} {'Type':<6} {'Cost':<12} {'Reasoning'}")
    print("-"*100)
    for i, m in enumerate(chain, 1):
        reasoning = "Yes" if m.get("has_reasoning") else "No"
        print(f"{i:<4} {m['model']:<55} {m['provider']:<12} {m['type']:<6} ${m['cost_per_call']:<11.6f} {reasoning}")

    # Save to config
    output = {
        "discovered_at": discovered.get("discovered_at", time.strftime("%Y-%m-%d %H:%M:%S")),
        "providers": {
            "openrouter": bool(OR_KEY),
            "kilo": bool(KILO_KEY)
        },
        "fallback_chain": chain,
        "openrouter_free_vision": discovered.get("openrouter", {}).get("free", []),
        "openrouter_minimax_vision": discovered.get("openrouter", {}).get("minimax", []),
        "kilo_free_vision": discovered.get("kilo", {}).get("models", [])
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {args.output}")

    # Print script template
    print("\n" + "="*80)
    print("OCR FALLBACK SCRIPT TEMPLATE")
    print("="*80)
    print("""
# Add to your OCR worker script:

VISION_MODELS = [""")
    for m in chain:
        reasoning = " (reasoning)" if m.get("has_reasoning") else ""
        print(f'    "{m["provider"]}/{m["model"]}",  # {m["type"].upper()}{reasoning}')
    print("""]

# Provider configurations:
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
KILO_API_KEY = os.environ.get("KILO_API_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1"
KILO_URL = "https://api.kilo.ai/api/gateway"

def call_vision_ocr(image_b64: str, prompt: str = "Extract surname and given name.") -> dict:
    \"\"\"Call vision model with multi-provider fallback.\"\"\"
    for model_spec in VISION_MODELS:
        provider, model_id = model_spec.split("/", 1)
        url = OPENROUTER_URL if provider == "openrouter" else KILO_URL
        key = OPENROUTER_API_KEY if provider == "openrouter" else KILO_API_KEY

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": prompt}
            ]}],
            "max_tokens": 500
        }
        HEAD = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        req = urllib.request.Request(url + "/chat/completions", data=json.dumps(payload).encode(), headers=HEAD)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode())
            msg = resp["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning", "") or ""
            return {"works": True, "model": f"{provider}/{model_id}", "content": content.strip()}
        except Exception:
            continue
    return {"works": False}
""")


if __name__ == "__main__":
    main()
