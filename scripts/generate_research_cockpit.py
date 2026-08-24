#!/usr/bin/env python3
"""Generate a static HTML research cockpit from a schema-valid research envelope.

Security model (Gate 1):
  * The dataset is embedded in a NON-EXECUTABLE ``<script type="application/json">``
    block. Raw ``json.dumps`` is never placed inside an executable ``<script>``.
  * All ``<`` characters are escaped as ``\\u003c`` and the Unicode line/paragraph
    separators U+2028/U+2029 are escaped, so a hostile vendor string containing
    ``</script>`` or separators cannot break out of or subvert the document.
  * Every research row is built with ``createElement`` + ``textContent``; no
    ``innerHTML`` is ever fed untrusted data.
  * Only HTTP/HTTPS links are permitted, each rendered with
    ``rel="noopener noreferrer"``.
  * A restrictive static CSP is emitted using explicit content hashes for the
    inline style and script blocks — never ``'unsafe-inline'``.

Validation is delegated to the canonical ``validate_research_schema`` library so
the cockpit cannot write an envelope that fails schema or state invariants, and
unsupported schema versions are rejected.

``--check`` (read-only, never writes):
  * validates the input envelope via the canonical library;
  * renders the expected HTML in memory;
  * fails if the output file is missing or its bytes differ from the expected
    render (stale);
  * verifies the embedded dataset digest and entity count match the input.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "research" / "schemas"
INPUT_PATH = ROOT / "research" / "processed" / "entities.json"
OUTPUT_PATH = ROOT / "docs" / "prototypes" / "research-cockpit" / "index.html"

VALID_SCHEMES = {"http", "https"}

STYLE_CSS = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; }
    h1 { color: #333; }
    .controls { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
    select, input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; }
    th { background: #f5f5f5; }
    tr:hover { background: #fafafa; }
    .score { font-weight: bold; }
    .score-high { color: #2e7d32; }
    .score-medium { color: #ed6c02; }
    .score-low { color: #c62828; }
    .state { font-family: monospace; }
    .empty { color: #888; font-style: italic; }
"""

APP_JS = """
    "use strict";
    var VALID_SCHEMES = ["http", "https"];

    function allowedLink(href) {
      try { return VALID_SCHEMES.indexOf(new URL(href).protocol.replace(":", "")) !== -1; } catch (e) { return false; }
    }

    function capState(offerings, key) {
      var o = offerings && offerings[key];
      return o ? o.state : "unknown";
    }

    function buildOption(select, value) {
      var opt = document.createElement("option");
      opt.value = value; opt.textContent = value;
      select.appendChild(opt);
    }

    var rawPayload = document.getElementById("research-data").textContent;
    var DATA;
    try {
      DATA = JSON.parse(rawPayload);
    } catch (e) {
      DATA = { entities: [], run_status: "parse-error" };
      console.error("Failed to parse embedded research data:", e);
    }

    function render() {
      var tbody = document.getElementById("results-body");
      tbody.textContent = "";
      var entities = (DATA && DATA.entities) || [];
      if (!entities.length) {
        var tr = document.createElement("tr");
        var td = document.createElement("td");
        td.colSpan = 12;
        td.className = "empty";
        td.textContent = "No entities yet. Research lanes are collecting (status: " + (DATA ? DATA.run_status : "unknown") + ").";
        tr.appendChild(td); tbody.appendChild(tr);
        return;
      }
      entities.forEach(function (e) {
        var tr = document.createElement("tr");
        var cells = [];
        var tdName = document.createElement("td");
        var a = document.createElement("a");
        var links = (e.source_links && e.source_links.length) ? e.source_links[0] : "#";
        if (links && links !== "#" && allowedLink(links)) {
          a.href = links; a.target = "_blank"; a.rel = "noopener noreferrer";
        } else { a.href = "#"; }
        a.textContent = e.title || "#";
        tdName.appendChild(a);
        var vals = [
          e.kind || "#",
          e.cohort || "#",
          e.geography || "#",
          capState(e.offerings, "received_invoice_processing"),
          capState(e.offerings, "issued_invoice_generation"),
          (e.target_customer) || "#",
          (e.pricing && e.pricing.public_status) || "#",
          (e.github_metrics && e.github_metrics.license) || "#",
          e.practical_business_use || "#"
        ];
        cells.push(tdName);
        vals.forEach(function (v) {
          var td = document.createElement("td");
          td.textContent = v;
          cells.push(td);
        });
        var score = (e.scores && typeof e.scores.overall === "number") ? e.scores.overall : 0;
        var scoreClass = score >= 70 ? "score-high" : score >= 40 ? "score-medium" : "score-low";
        var tdScore = document.createElement("td");
        tdScore.className = "score " + scoreClass;
        tdScore.textContent = score;
        cells.push(tdScore);
        var tdVer = document.createElement("td");
        tdVer.textContent = e.last_verified || "#";
        cells.push(tdVer);
        cells.forEach(function (c) { tr.appendChild(c); });
        tbody.appendChild(tr);
      });
    }

    function populateFilters() {
      var entities = (DATA && DATA.entities) || [];
      var cohortS = document.getElementById("cohort-filter");
      var custS = document.getElementById("customer-filter");
      var priceS = document.getElementById("pricing-filter");
      var evS = document.getElementById("evidence-filter");
      var licS = document.getElementById("license-filter");
      var pracS = document.getElementById("practical-filter");
      uniqueOptions(cohortS, entities.map(function (e) { return e.cohort; }));
      uniqueOptions(custS, entities.map(function (e) { return e.target_customer; }));
      uniqueOptions(priceS, entities.map(function (e) { return e.pricing && e.pricing.public_status; }));
      uniqueOptions(evS, entities.map(function (e) { return (e.evidence_states || []); }).reduce(function (a, b) { return a.concat(b); }, []));
      uniqueOptions(licS, entities.map(function (e) { return e.github_metrics && e.github_metrics.license; }));
      uniqueOptions(pracS, entities.map(function (e) { return e.practical_business_use; }));
    }

    function uniqueOptions(select, values) {
      var seen = {};
      values.filter(Boolean).forEach(function (v) {
        if (!seen[v]) { seen[v] = true; buildOption(select, v); }
      });
    }

    function applyFilters() {
      var cf = document.getElementById("cohort-filter").value;
      var df = document.getElementById("direction-filter").value;
      var cuf = document.getElementById("customer-filter").value;
      var pf = document.getElementById("pricing-filter").value;
      var lf = document.getElementById("license-filter").value;
      var prf = document.getElementById("practical-filter").value;
      var original = (DATA && DATA.entities) || [];
      DATA.entities = original.filter(function (e) {
        if (cf && e.cohort !== cf) return false;
        if (cuf && e.target_customer !== cuf) return false;
        if (pf && e.pricing && e.pricing.public_status !== pf) return false;
        if (lf && (!e.github_metrics || e.github_metrics.license !== lf)) return false;
        if (prf && e.practical_business_use !== prf) return false;
        if (df) {
          var r = capState(e.offerings, "received_invoice_processing");
          var i = capState(e.offerings, "issued_invoice_generation");
          var both = (r === "confirmed" && i === "confirmed");
          if (df === "received" && r !== "confirmed") return false;
          if (df === "issued" && i !== "confirmed") return false;
          if (df === "both" && !both) return false;
        }
        return true;
      });
      render();
      DATA.entities = original;
    }

    document.getElementById("cohort-filter").addEventListener("change", applyFilters);
    document.getElementById("direction-filter").addEventListener("change", applyFilters);
    document.getElementById("customer-filter").addEventListener("change", applyFilters);
    document.getElementById("pricing-filter").addEventListener("change", applyFilters);
    document.getElementById("license-filter").addEventListener("change", applyFilters);
    document.getElementById("practical-filter").addEventListener("change", applyFilters);
    document.getElementById("sort-select").addEventListener("change", function () {
      var v = this.value;
      var arr = (DATA && DATA.entities) || [];
      if (v === "title") arr.sort(function (a, b) { return (a.title || "").localeCompare(b.title || ""); });
      else if (v === "overall_score") arr.sort(function (a, b) { return ((b.scores && b.scores.overall) || 0) - ((a.scores && a.scores.overall) || 0); });
      else if (v === "last_verified") arr.sort(function (a, b) { return (b.last_verified || "").localeCompare(a.last_verified || ""); });
      render();
    });

    var meta = document.getElementById("meta");
    var m = document.createElement("p");
    m.className = "state";
    m.textContent = "run_id=" + (DATA ? DATA.run_id : "?") + " as_of=" + (DATA ? DATA.as_of : "?") + " status=" + (DATA ? DATA.run_status : "?");
    meta.appendChild(m);

    populateFilters();
    render();
"""


def _csp_hash(s: str) -> str:
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


CSP = (
    "default-src 'self'; "
    "script-src 'self' 'sha256-{js}'; "
    "style-src 'self' 'sha256-{css}'; "
    "img-src 'self' data:; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'none'"
).format(js=_csp_hash(APP_JS), css=_csp_hash(STYLE_CSS))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="__CSP__">
  <title>Research Cockpit — Accounting Automation</title>
  <style>__STYLE__</style>
</head>
<body>
  <h1>Accounting Automation Research Cockpit</h1>
  <div id="meta"></div>
  <div class="controls">
    <select id="cohort-filter"><option value="">All Cohorts</option></select>
    <select id="direction-filter"><option value="">All Directions</option><option value="received">Received</option><option value="issued">Issued</option><option value="both">Both</option></select>
    <select id="customer-filter"><option value="">All Customers</option></select>
    <select id="pricing-filter"><option value="">All Pricing</option></select>
    <select id="evidence-filter"><option value="">All Evidence</option></select>
    <select id="license-filter"><option value="">All Licenses</option></select>
    <select id="practical-filter"><option value="">All Practical Use</option></select>
    <select id="sort-select">
      <option value="title">Sort: Title</option>
      <option value="overall_score">Sort: Score</option>
      <option value="last_verified">Sort: Last Verified</option>
    </select>
  </div>
  <table id="results-table">
    <thead>
      <tr>
        <th>Name</th><th>Kind</th><th>Cohort</th><th>Geo</th>
        <th>Received</th><th>Issued</th><th>Customer</th><th>Pricing</th>
        <th>License</th><th>Practical</th><th>Score</th><th>Last Verified</th>
      </tr>
    </thead>
    <tbody id="results-body"></tbody>
  </table>
  <script type="application/json" id="research-data">__DATA_JSON__</script>
  <script>__APP_JS__</script>
</body>
</html>"""


def safe_json_payload(data: object) -> str:
    """Serialize ``data`` so it is safe to embed inside an HTML data block.

    Escapes ``<`` (so ``</script>`` cannot terminate the block) and the Unicode
    separators U+2028 / U+2029 which are otherwise valid in JSON but illegal in
    JavaScript string literals.
    """
    text = json.dumps(data, ensure_ascii=False)
    text = text.replace("<", "\\u003c").replace(">", "\\u003e")
    text = text.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return text


def data_digest(data: object) -> str:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def render_html(data: dict) -> str:
    return (HTML_TEMPLATE
            .replace("__CSP__", CSP)
            .replace("__STYLE__", STYLE_CSS)
            .replace("__APP_JS__", APP_JS)
            .replace("__DATA_JSON__", safe_json_payload(data)))


def validate_input(root: Path, data: dict) -> tuple[bool, str]:
    """Canonical envelope validation (schema + relationship/state)."""
    try:
        from scripts.validate_research_schema import validate_envelope
    except Exception:
        sys.path.insert(0, str(ROOT))
        from scripts.validate_research_schema import validate_envelope
    ok, detail, _ = validate_envelope(root, data)
    return ok, detail


def run_check(root: Path, input_path: Path, output_path: Path, data: dict) -> int:
    ok, detail = validate_input(root, data)
    if not ok:
        print("CHECK FAIL: schema/state — " + detail, file=sys.stderr)
        return 1

    expected = render_html(data)
    digest = data_digest(data)
    entity_count = len(data.get("entities", []) or [])

    if not output_path.is_file():
        print("CHECK FAIL: output missing: %s" % output_path, file=sys.stderr)
        return 1

    current = output_path.read_text(encoding="utf-8")
    if current != expected:
        print("CHECK FAIL: output is stale (bytes differ from fresh render)", file=sys.stderr)
        return 1

    # Verify the embedded dataset digest and entity count actually match the input.
    import re as _re
    m = _re.search(r'<script type="application/json" id="research-data">(.*?)</script>', current, _re.DOTALL)
    if not m:
        print("CHECK FAIL: embedded dataset block not found", file=sys.stderr)
        return 1
    try:
        embedded = json.loads(m.group(1))
    except Exception as exc:
        print("CHECK FAIL: embedded dataset is not valid JSON: %s" % exc, file=sys.stderr)
        return 1
    if data_digest(embedded) != digest:
        print("CHECK FAIL: embedded dataset digest does not match input", file=sys.stderr)
        return 1
    if len(embedded.get("entities", []) or []) != entity_count:
        print("CHECK FAIL: embedded entity count does not match input", file=sys.stderr)
        return 1

    print("CHECK PASS: schema ok; digest=%s; entities=%d; output current" % (digest[:16], entity_count))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate research cockpit")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--input", default=None, help="Envelope input path")
    parser.add_argument("--output", default=None, help="HTML output path")
    parser.add_argument("--check", action="store_true", help="Read-only validation check")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    input_path = Path(args.input).resolve() if args.input else (root / "research" / "processed" / "entities.json")
    output_path = Path(args.output).resolve() if args.output else (root / "docs" / "prototypes" / "research-cockpit" / "index.html")

    if not input_path.is_file():
        print("ERROR: envelope not found: %s" % input_path, file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print("ERROR: invalid envelope JSON: %s" % exc, file=sys.stderr)
        sys.exit(1)

    if args.check:
        sys.exit(run_check(root, input_path, output_path, data))

    ok, detail = validate_input(root, data)
    if not ok:
        print("REFUSE: will not render invalid envelope — " + detail, file=sys.stderr)
        sys.exit(1)

    html = render_html(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print("Wrote cockpit: %s (entities=%d)" % (output_path, len(data.get("entities", []) or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
