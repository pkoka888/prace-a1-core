# AI Infrastructure and Library Findings — 2026-08-11

> **Status: Historical research — do not execute.** Provider rosters, prices,
> quotas, packages, and recommendations are time-sensitive. Reverify primary
> sources under current `AGENTS.md`; active plans and approved decisions prevail.

Status: research only, via official docs + primary repos + live API snapshots
(context7 free quota was exhausted; findings below replace the blocked context7
queries). All sources accessed 2026-08-11. Litellm and n8n are assumed to be
available on the host/planning soon and are counted as infrastructure.

Reference policy: AGENTS.md "AI Provider, Model and Cost Policy" — free-only
external model use; the Codex subscription is the only authorized paid AI access;
no credit purchases, billing activation or paid fallbacks.

---

## 1. OpenRouter — free vision models and /api/v1/models (Plan A)

### Discovery API (official)
- `GET https://openrouter.ai/api/v1/models` is **public / unauthenticated**.
  Response root: `data[]`, `total_count`, `links.next` (null = unpaginated).
  Source: https://openrouter.ai/docs/guides/overview/models.md
- Model fields: `id`, `canonical_slug`, `name`, `created`, `description`,
  `context_length`, `architecture`, `pricing`, `top_provider`, `per_request_limits`,
  `supported_parameters`, `default_parameters`, `expiration_date`, `benchmarks`.
- `pricing` is a JSON object of **string** USD values: `prompt`, `completion`,
  `request`, `image`, `web_search`, `internal_reasoning`, `input_cache_read`,
  `input_cache_write`, `overrides`. Docs: `"0"` = feature is free.
- **Image capability flag lives in `architecture.input_modalities` /
  `output_modalities` / `modality`** (e.g. `"modality": "text+image+file->text"`).
  `supported_parameters` is only the API-parameter list; `architecture.multimodal`
  was `null` on all 402 live entries.
- Free filter: `pricing.prompt == "0" && pricing.completion == "0"` plus image
  capability in `architecture.input_modalities`.

### Free-model conventions (official)
- `:free` suffix documented: "Append `:free` to any model ID"
  (https://openrouter.ai/docs/guides/routing/model-variants/free.md).
- `openrouter/free` router is official, appears in the catalog itself with 0/0
  pricing and `text+image->text`; supports `response_format` + `structured_outputs`
  (https://openrouter.ai/docs/guides/routing/routers/free-router.md).
- No official `?q=free` API filter. Website filter URLs exist:
  `https://openrouter.ai/models?pricing=free` and `?max_price=0`; collection:
  https://openrouter.ai/collections/free-models
- Single-model lookup: `GET /api/v1/model/{author}/{slug}` (supports `:free`).

### Rate limits (official — critical for Plan A)
- **20 requests/min** at every tier.
- **50 requests/day** if < $10 credits purchased all-time.
- **1000 requests/day** if >= $10 credits purchased all-time (one-time top-up
  counts, even after balance drops).
- Free-model limits are **account-wide**, not per model. `X-RateLimit-*` headers
  appear only on 429 responses. 429 handling: exponential backoff + `Retry-After`.
- 402 (Payment Required) can still hit free models if balance is negative.
- Source: https://openrouter.ai/docs/api_reference/limits.md (also free.md, faq.md)

> **Policy consequence:** the 1000/day tier requires >= $10 lifetime credits, which
> the AGENTS.md cost policy **prohibits**. Plan A must therefore budget for
> **~50 requests/day** and batch crops per page to fit within it.

### Verified free vision-capable models (live /api/v1/models snapshot, 2026-08-11)
- `google/gemma-4-26b-a4b-it:free` — text+image+video->text, 256k ctx; supports
  `response_format` + `structured_outputs` → **best fit for strict-JSON QA**.
- `google/gemma-4-31b-it:free` — text+image+video->text, 256k ctx.
- `nvidia/nemotron-nano-12b-v2-vl:free` — text+image+video->text, 128k ctx; no
  structured outputs.
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` — text+image+audio+video.
- `openrouter/free` — router, text+image->text, structured outputs.
- NOT confirmed free (despite guesses): no gemma-3.4, no qwen3-vl:free, no
  llama-*-vision:free. Free roster changes frequently → always re-discover at
  runtime via the filter above.

### Image inputs (official)
- OpenAI-style content array: `{type:"text", text:...}` + `{type:"image_url",
  image_url:{url:...}}`; `url` can be public or base64 `data:image/jpeg;base64,...`.
  Multiple images = multiple content entries; text-first recommended.
  MIME: png/jpeg/webp/gif. PDFs are a separate documented path.
  Source: https://openrouter.ai/docs/guides/overview/multimodal/image-understanding.md

### Action for Plan A
- Pin `google/gemma-4-26b-a4b-it:free` as primary and `openrouter/free` as
  documented fallback; re-discover at runtime; budget ~50 req/day; batch all field
  crops of a page into one request (multi-image content array); run deterministic
  geometry checks before any vision call.

---

## 2. PyMuPDF + pypdf — rendering, cropping, verification (Plans A/B)

### PyMuPDF (fitz / pymupdf)
- `Page.get_pixmap(*, matrix, dpi=None, colorspace, clip=None, alpha=False, annots=True)`:
  `dpi=300` renders at exactly 300 DPI **and saves DPI with the PNG** (Matrix does
  not). `alpha=False` (default) = white/opaque background.
  Sources: https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_pixmap ,
  https://pymupdf.readthedocs.io/en/latest/recipes-images.html
- Clip cropping in one call: `page.get_pixmap(matrix=..., clip=rect)` renders only
  `clip ∩ page` — exact 300-DPI field-section crops without whole-page renders.
  (https://pymupdf.readthedocs.io/en/latest/recipes-images.html#how-to-create-partial-pixmaps-clips)
- Baselines from text: `page.get_text("dict")` → per-span keys `origin` (y = first
  char baseline), `ascender`/`descender`, `bbox`, `font`, `size`, `flags`,
  `char_flags` (invisible-text detection, added 1.25.2), `alpha`.
  Docs show the baseline formula `r.y1 = o.y - span["size"] * d / (a - d)`.
  Source: https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
- **pypdf has no page-rasterization API at all** (pure Python). All rendering/crops
  must use PyMuPDF; pypdf is for form/widget/text-matrix work only.
- Versions: **PyMuPDF 1.28.2** (2026-08-06), Python 3.10–3.14. Legacy `import fitz`
  now warns; use `import pymupdf`. 1.26.0 removed `save(linear=True)`.
  Source: https://pypi.org/project/PyMuPDF/ , https://pymupdf.readthedocs.io/en/latest/changes.html

### pypdf
- Detect fields: `reader.get_fields()` returns None if no AcroForm fields;
  `reader.get_form_text_fields()` = {name: text}. Strict zero-widget check: iterate
  `page.annotations` matching `Subtype == "/Widget"` and/or inspect
  `reader.root_object["/AcroForm"]["/Fields"]`.
  Sources: https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html#pypdf.PdfReader.get_fields ,
  https://pypdf.readthedocs.io/en/stable/user/forms.html
- Flatten: `writer.update_page_form_field_values(page, {...}, flatten=True)` then
  `writer.remove_annotations(subtypes="/Widget")`; use `auto_regenerate=False`.
  (https://pypdf.readthedocs.io/en/stable/user/forms.html#filling-out-forms)
- Baselines via visitor: `page.extract_text(visitor_text=func)` where
  `func(text, cm, tm, font_dict, font_size)`; `tm[5]` is y-translation (baseline y);
  docs recommend `cm` user matrix as it includes all transforms. "In complicated
  documents, the calculated positions may be difficult to determine."
  Source: https://pypdf.readthedocs.io/en/stable/user/extract-text.html#using-a-visitor
- Versions: **pypdf 6.15.0** (2026-08-06); flattening matured in 5.8.0+; 6.0.0
  dropped Python 3.8.

---

## 3. RapidOCR — OCR engine for Plan B (Czech documents)

### Versions and package split
- `rapidocr` **3.9.2** (PyPI wheel 2026-07-21; Apache-2.0; bundles default models;
  current unified engine-agnostic package).
- `rapidocr-onnxruntime` 1.4.4 is the **legacy v1.x** ONNX-only package; its
  `__call__` returns a tuple `(result, elapse)`, unlike the v3 dataclass.
- Our host has rapidocr 3.9.2 (current) + rapidocr-onnxruntime 1.2.3 (legacy) →
  use the **v3 API**.
- Sources: https://pypi.org/pypi/rapidocr/json , https://github.com/RapidAI/RapidOCR/releases

### Languages / Czech diacritics
- Default pack (>=3.9.0): PP-OCRv6 small det + PP-OCRv4 mobile cls + PP-OCRv6 small
  rec (Chinese+English).
- **Latin model paths (official):** PP-OCRv5 `latin` rec model explicitly covers
  **Czech** (plus EN/FR/DE/SK/PL…); select via
  `"Rec.ocr_version": OCRVersion.PPOCRV5`, `"Rec.lang_type": LangRec.LATIN`.
  PP-OCRv6 rec small/medium is a single multi-language model whose supported
  languages include `cs` (Czech) and `sk`.
  Source: https://rapidai.github.io/RapidOCRDocs/main/model_list/
- No documented diacritics-specific limitation found in official docs.

### Capabilities vs PaddleOCR
- Engines: ONNX Runtime (CPU/GPU), OpenVINO, Paddle, PyTorch, MNN, TensorRT.
  CPU recommended; GPU can be *slower* due to dynamic input shape (official FAQ).
- **Orientation classification EXISTS** but only 0/180 line flips (Cls module,
  `cls_thresh` 0.9). **Document unwarping does NOT exist** (no de-warp module;
  preprocessing is resize + padding only).
- New in 3.9.2: padding params `min_height`, `width_height_ratio`,
  `use_vertical_padding` for thin/low-height scans.
- Source: https://rapidai.github.io/RapidOCRDocs/main/faq/faq/ ,
  https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/parameters/

### API (v3)
- `from rapidocr import RapidOCR; engine = RapidOCR(); out = engine(img)`.
  Returns dataclass `RapidOCROutput`: `.img`, `.boxes` (N,4,2), `.txts`,
  `.scores`, `.word_results`, `.elapse_list`, `.elapse`, `.lang_rec`.
- Config: `RapidOCR(config_path="1.yaml")` or `RapidOCR(params={"Det.thresh": 0.3})`.
- Accuracy params (v3 names): `Global.text_score` (0.5), `Global.use_det/use_cls/use_rec`,
  `Global.min_side_len` (30), `Global.max_side_len` (2000); Det: `thresh` (0.3),
  `box_thresh` (0.5), `unclip_ratio` (1.6), `use_dilation` (True); Cls: `cls_thresh`
  (0.9). The v1 names (`det_thresh`, `rec_score_thresh`, `det_model_dir`) are legacy.
- Maintainer SWHL; active (v3.9.2, 2026-07-21; ~7.5k stars). Models © Baidu.

### Action for Plan B
- Port `employee_scan_processor.py` to the **v3 API** (`rapidocr` package), keep
  the Latin/Czech config (PP-OCRv5 latin or PP-OCRv6 with `cs`), and retain local
  OCR first; OpenRouter OCR stays a free-only fallback.

---

## 4. n8n — automation platform (Plan C)

### Release and license
- Stable 2.33.7 / latest tag n8n@2.34.4 (2026-08-07). License unchanged since
  2022: **Sustainable Use License (SUL)** — fair-code, not OSI; self-hosting for
  internal business use is allowed; `.ee.` files are Enterprise-licensed.
  Sources: https://docs.n8n.io/privacy-and-security/sustainable-use-license ,
  https://github.com/n8n-io/n8n/blob/master/LICENSE.md

### Facebook/Instagram
- No dedicated Instagram app node. Use the **Facebook Graph API** node
  (`n8n-nodes-base.facebookgraphapi`): generic GET/POST/DELETE against
  graph.facebook.com; used for Page feed (`/{page-id}/feed`) and Instagram
  media→media_publish container flow. Auth: OAuth2 or App access token (OAuth2
  added in 2.22).
  Source: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.facebookgraphapi
- **Facebook Trigger** node supports Instagram objects (comments, mentions,
  messages, insights) for Business/Creator accounts.
- Meta permissions: Page posting = `pages_manage_posts` (+`pages_read_engagement`,
  `pages_show_list`); Instagram = `instagram_basic` + `instagram_content_publish`
  + `pages_read_engagement`. App review only needed for OTHER users' accounts;
  own-account posting works in Development mode with tester/admin.
  Sources: https://developers.facebook.com/docs/instagram-platform/content-publishing ,
  https://developers.facebook.com/docs/permissions/reference/instagram_content_publish
- Community node (unofficial): `@mookielianhd/n8n-nodes-instagram` v3.4.0.

### HTTP / webhook / credentials
- HTTP Request node: full verbs, JSON/form/binary, pagination, auth via generic or
  predefined credentials (Header auth `Authorization: Bearer …` suits OpenRouter
  and job APIs).
- Webhook trigger: Basic/Header/JWT auth, IP whitelist, CORS, 16 MB max payload.
- Credentials are **encrypted at rest** with the instance encryption key; set a
  fixed `N8N_ENCRYPTION_KEY` (changing it breaks stored credentials).
- Sources: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest ,
  https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key

### Audit logging / GDPR
- Execution history (per-run I/O, timestamps) is **core and free**; default prune
  14 days / 10,000 executions (annotated executions never pruned).
- **Native audit-log streaming is Enterprise-only** (log streaming destinations;
  `anonymizeAuditMessages`).
- `n8n audit` security CLI is free (credentials/DB/fs/nodes/instance risks).
- For our access-logging need: retain execution history and/or build a custom
  audit-log workflow; SIEM-ready events require Enterprise.
- Sources: https://docs.n8n.io/administer/observe-and-log/stream-logs-to-external-systems ,
  https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/manage-execution-data

### Deployment
- Official Docker image `docker.n8n.io/n8nio/n8n`; PostgreSQL recommended
  (`DB_TYPE=postgresdb`); docker-compose stacks in `n8n-io/n8n-hosting`.
- Meta OAuth2 redirect URL must be publicly reachable; app-access-token method
  works on localhost. Webhooks from Meta need a public `WEBHOOK_URL`.
- Community edition free with almost all features; Business/Enterprise add SSO,
  LDAP, log streaming/audit, environments, workflow approval.
- Bottom line: FB/IG posting + job-feed syndication are fully supported on
  self-hosted Community; native audit streaming needs Enterprise (build your own).

---

## 5. LiteLLM — gateway for free-only routing

### Version and concepts
- Stable **v1.96.0** (2026-08-09); weekly releases; repo BerriAI/litellm.
  Proxy Server = unified OpenAI-format gateway with virtual keys + spend tracking.
  Sources: https://docs.litellm.ai/docs/simple_proxy ,
  https://github.com/BerriAI/litellm/releases

### Free models (official)
- **Zero-cost models bypass all budget checks**: set `input_cost_per_token: 0`
  and `output_cost_per_token: 0` explicitly (null/undefined → treated as costed).
  Zero-cost ⇒ `skip_budget_checks`.
  Sources: https://docs.litellm.ai/docs/proxy/custom_pricing ,
  https://docs.litellm.ai/docs/proxy/users
- Local/Ollama models (`ollama/llama3`, `api_base: http://localhost:11434`) are the
  natural zero-cost path.

### Cost metadata and verification
- `/v1/models?include_metadata=true` returns only `fallbacks` today (pricing is a
  planned extension point, NOT returned now). Open feature request #21855.
  Source: https://docs.litellm.ai/docs/proxy/model_access
- `GET /model/info` (admin route) returns mapped cost + context + custom
  `model_info` — the only price-metadata endpoint, and admin-only. **No read-only
  endpoint lets a virtual-key caller verify price/zero-cost before a request.**
  → For "verify zero-cost before send": use admin `/model/info`, static config
  inspection, or a pinned allowlist of known-free model IDs.
- `POST /reload/model_cost_map` (admin; v1.76.0+) reloads
  `model_prices_and_context_window.json` pricing without restart.
  Sources: https://docs.litellm.ai/docs/proxy/model_management ,
  https://docs.litellm.ai/docs/proxy/sync_models_github

### Auth and budgets
- `master_key` (admin, `sk-...`) in `general_settings.master_key` /
  `LITELLM_MASTER_KEY`; virtual keys via `/key/generate`.
- Per-key `max_budget` blocks requests once exceeded, **but zero-cost models skip
  budget checks** → for free-only enforcement use the key's **models allowlist**
  (restrict to free model names) plus config review, not budgets.
- Sources: https://docs.litellm.ai/docs/proxy/virtual_keys ,
  https://docs.litellm.ai/docs/proxy/model_access

### License and enterprise split
- MIT for code outside `enterprise/`; `enterprise/` is commercial. OSS keeps:
  virtual keys, users, teams, spend/budgets/rate limits, fallbacks, logging,
  Prometheus metrics. Enterprise adds: SSO>5 users, SCIM, audit logs, key
  rotation/secret managers, org/team RBAC, IP allowlists.
- Community issue #34241 claims the MIT/Enterprise line is not physically enforced
  — treat as compliance caveat, unconfirmed by BerriAI.
- Source: https://docs.litellm.ai/docs/enterprise

---

## Cross-plan consequences

- **Plan A:** budget the vision loop at ~50 OpenRouter req/day (no credits);
  batch crops per page; pin `google/gemma-4-26b-a4b-it:free` primary,
  `openrouter/free` fallback; deterministic geometry before vision. PyMuPDF
  1.28.2 `get_pixmap(dpi=300, clip=...)` + `get_text("dict")` baselines are the
  render/QA primitives.
- **Plan B:** RapidOCR v3 API with Czech-capable Latin/`cs` models (orientation
  = 0/180 only, no unwarping); port `employee_scan_processor.py` accordingly;
  OpenRouter OCR remains free-only fallback.
- **Plan C:** n8n Community (self-hosted) covers FB/IG publishing + feed
  syndication; build own audit-log store; litellm (once available) can route
  free-only models if per-key allowlists pin known-free IDs — do NOT rely on
  budgets or `/v1/models` metadata for zero-cost verification.
