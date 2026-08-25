# Multi-Provider Vision Model Research Report

**Date:** 2026-08-25
**Repository:** `pkoka888/prace-v-nemecku`

---

## 1. API Provider Comparison

### 1.1 OpenRouter (Primary - Has API Key)

**Base URL:** `https://openrouter.ai/api/v1`
**Authentication:** `Authorization: Bearer {API_KEY}`

| Aspect | Details |
|--------|---------|
| **Free tier** | 17 models available |
| **Vision models** | 4 working (2 free, 2 paid) |
| **Vision endpoint** | `/chat/completions` with `image_url` content parts |
| **Rate limits** | 429 Too Many Requests on free models |
| **Cost tracking** | Per-request `usage.cost` field |

**Free Vision Models:**
| Model | Cost | Reasoning |
|-------|------|-----------|
| `minimax/minimax-m3:free` | $0 | No |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | $0 | Yes |

**Paid Vision Models (MiniMax):**
| Model | Cost/1M tokens | Reasoning |
|-------|-----------------|-----------|
| `minimax/minimax-01` | $0.20 | No |
| `minimax/minimax-m3` | $0.30 | Yes |

### 1.2 Kilo Gateway (Secondary - No API Key Currently)

**Base URL:** `https://api.kilo.ai/api/gateway`
**Authentication:** `Authorization: Bearer {API_KEY}`
**Model Format:** `provider/model-name` (e.g., `anthropic/claude-sonnet-4.6`)

**Features:**
- Unified OpenAI-compatible API
- BYOK (Bring Your Own Key) support
- Usage tracking with microdollar precision
- Organization controls (allow lists, spending limits)
- 500+ models through single endpoint

**Known Free Models:**
| Model | Description |
|-------|-------------|
| `stepfun/step-3.7-flash:free` | StepFun Step 3.7 Flash |
| `poolside/laguna-s-2.1:free` | Poolside Laguna S 2.1 |
| `poolside/laguna-xs-2.1:free` | Poolside Laguna XS 2.1 |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | NVIDIA Nemotron 3 Ultra |
| `tencent/hy3:free` | Tencent Hy3 |
| `openrouter/free` | Best available free model |

**Important:** The Kilo config in `~/.config/kilo/kilo.jsonc` uses `kilo/` prefix for internal routing (e.g., `kilo/poolside/laguna-xs-2.1:free`). The API itself uses `provider/model-name` format.

### 1.3 Other Providers (Tested - No Working Vision)

| Provider | API Status | Notes |
|----------|-----------|-------|
| DeepSeek | 402 Payment Required | Has vision model `deepseek-v4-flash-vision-exp` but no credits |
| Groq | 403 Forbidden | API key invalid/expired |
| Cerebras | 403 Forbidden | API key invalid/expired |

---

## 2. Vision Model Discovery Results

### 2.1 OpenRouter Free Models Tested

**Total tested:** 28 models (17 free + 11 MiniMax)

**Working Vision Models:**
```
1. minimax/minimax-m3:free         - FREE, $0, no reasoning
2. nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free - FREE, $0, has reasoning
3. minimax/minimax-01              - PAID, $0.20/1M, no reasoning
4. minimax/minimax-m3              - PAID, $0.30/1M, has reasoning
```

**Failed Models:**
| Model | Error | Reason |
|-------|-------|--------|
| `thinkingmachines/inkling-small:free` | 403 Forbidden | "Only available on agentic harnesses" |
| `thinkingmachines/inkling:free` | 403 Forbidden | "Only available on agentic harnesses" |
| Most NVIDIA free models | 404 Not Found | "No endpoints found that support image input" |
| `google/gemma-4-26b-a4b-it:free` | 429 Rate Limited | Too many requests |
| `google/gemma-4-31b-a4b-it:free` | 429 Rate Limited | Too many requests |

### 2.2 Key Finding: Model Routing Differences

The error message for `thinkingmachines/inkling:free` says:
> "Only available on agentic harnesses. Try plugging in..."

This suggests OpenRouter routes some models through agentic harnesses (like Kilo) rather than direct API access. This is why:
- Kilo config uses `kilo/` prefix for some models
- OpenRouter has models that only work through specific gateways

---

## 3. Multi-Provider Fallback Architecture

### 3.1 Provider Selection Logic

```
┌─────────────────────────────────────────────────────────┐
│                    OCR Request                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│          OpenRouter (Primary - Has Key)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. minimax/minimax-m3:free (FREE)              │   │
│  │ 2. nvidia/nemotron-3-nano-omni:free (FREE)   │   │
│  │ 3. minimax/minimax-m3 (PAID, reasoning)        │   │
│  │ 4. minimax/minimax-01 (PAID)                  │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                             │
│              Success? ──┴ ─── Fail ──► Next Model     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ All OpenRouter Failed
                  ▼
┌─────────────────────────────────────────────────────────┐
│            Kilo Gateway (Secondary)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. kilo-auto/free (dynamic routing)            │   │
│  │ 2. stepfun/step-3.7-flash:free                │   │
│  │ 3. Other Kilo free models...                    │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                             │
│              Success? ──┴ ─── Fail ──► Next Model     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ All Failed
                  ▼
         Return Error / Local OCR
```

### 3.2 API Call Format

**OpenRouter:**
```python
url = "https://openrouter.ai/api/v1/chat/completions"
model = "minimax/minimax-m3:free"  # Just the model ID
headers = {"Authorization": f"Bearer {OR_KEY}"}
```

**Kilo Gateway:**
```python
url = "https://api.kilo.ai/api/gateway/chat/completions"
model = "minimax/minimax-m3"  # Just the model ID (no :free suffix for paid)
headers = {"Authorization": f"Bearer {KILO_KEY}"}
```

### 3.3 Content Part Format (Vision)

Both providers support OpenAI-compatible `image_url` content parts:

```python
messages = [{
    "role": "user",
    "content": [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        },
        {
            "type": "text",
            "text": "Extract surname and given name."
        }
    ]
}]
```

---

## 4. Kilo Gateway Research

### 4.1 Official Documentation Summary

**Documentation URL:** https://kilo.ai/docs/gateway

**Key Points:**
1. **Base URL:** `https://api.kilo.ai/api/gateway`
2. **Model Format:** `provider/model-name` (e.g., `anthropic/claude-sonnet-4.6`)
3. **Free Models:** Listed in docs, require no credits
4. **Auto Models:** `kilo-auto/free`, `kilo-auto/frontier`, `kilo-auto/efficient`, `kilo-auto/small`

### 4.2 Kilo Configuration vs API

The Kilo CLI config (`~/.config/kilo/kilo.jsonc`) uses a different format than the Gateway API:

| Aspect | Kilo Config | Kilo Gateway API |
|--------|-------------|------------------|
| Model prefix | `kilo/` | No prefix |
| Example | `kilo/poolside/laguna-xs-2.1:free` | `poolside/laguna-xs-2.1:free` |
| Authentication | Config file | API key |

### 4.3 Kilo Auto Models

```
kilo-auto/free      → Dynamic routing to free models
kilo-auto/frontier  → Anthropic Claude Opus 4.7 for planning
kilo-auto/efficient → Qwen or Claude based on task difficulty
kilo-auto/small    → Gemma for lightweight background tasks
```

---

## 5. Script Usage

### 5.1 Discovery Script

```bash
# Full refresh + test
python3 scripts/list_vision_models.py --refresh --test

# OpenRouter only
python3 scripts/list_vision_models.py --openrouter-only --refresh

# Kilo only (needs KILO_API_KEY)
python3 scripts/list_vision_models.py --kilo-only --refresh
```

### 5.2 Output Files

| File | Description |
|------|-------------|
| `config/vision_models.json` | Fallback chain + metadata |
| `config/vision_models_cache.json` | Raw discovery results |

### 5.3 Integration

```python
from scripts.list_vision_models import call_vision_ocr

result = call_vision_ocr(
    image_b64=base64_image,
    prompt="Extract surname and given name as JSON."
)
if result["works"]:
    print(f"Model: {result['model']}")
    print(f"Content: {result['content']}")
```

---

## 6. Recommendations

### 6.1 Immediate (Current Setup)

1. **Use OpenRouter primary** - Has working vision models
2. **Fallback order:**
   - `minimax/minimax-m3:free` (primary, fastest)
   - `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` (secondary, more capable)
   - `minimax/minimax-01` (paid fallback, cheapest)
   - `minimax/minimax-m3` (paid, has reasoning for complex OCR)

3. **Rate limit handling:** Add retry with exponential backoff

### 6.2 Future (With Kilo API Key)

1. **Get Kilo API key** from https://app.kilo.ai
2. **Add Kilo as secondary fallback**
3. **Test Kilo free models** for vision:
   - `stepfun/step-3.7-flash:free`
   - `poolside/laguna-s-2.1:free`
   - `poolside/laguna-xs-2.1:free`

### 6.3 Alternative OCR

If all API-based OCR fails:
- **Local OCR:** Install `rapidocr` with `pip install rapidocr==3.9.2 onnxruntime`
- **Tesseract:** Install system package + `pytesseract`

---

## 7. Files Created

| File | Purpose |
|------|---------|
| `scripts/list_vision_models.py` | Multi-provider discovery + fallback |
| `config/vision_models.json` | Current fallback chain |
| `config/vision_models_cache.json` | Raw discovery cache |

---

## 8. Appendix: OpenRouter Complete Model List

### Free Models (17 total)
```
cohere/north-mini-code:free
dots-studio/dots-3-note-preview:free
google/gemma-4-26b-a4b-it:free
google/gemma-4-31b-it:free
liquid/lfm-2.5-2.6b:free
minimax/minimax-m2.7:free
minimax/minimax-m3:free  ← VISION WORKING
nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free  ← VISION WORKING
nvidia/nemotron-3-super-120b-a12b:free
nvidia/nemotron-3-ultra-550b-a55b:free
nvidia/nemotron-3.5-content-safety:free
nvidia/nemotron-3.5-lightning:free
poolside/laguna-s-2.1:free
poolside/laguna-xs-2.1:free
thinkingmachines/inkling-small:free
thinkingmachines/inkling:free
z-ai/glm-5.2:free
```

### MiniMax Models (All)
```
minimax/minimax-01              ← VISION WORKING (paid)
minimax/minimax-m1
minimax/minimax-m2
minimax/minimax-m2.1
minimax/minimax-m2.5
minimax/minimax-m2.7
minimax/minimax-m2.7:free     ← Not working (no vision endpoint)
minimax/minimax-m3             ← VISION WORKING (paid, reasoning)
minimax/minimax-m3:free        ← VISION WORKING (free)
minimax/minimax-m3:batch       ← Batch only, not for direct API
minimax/minimax-m2-her
```
