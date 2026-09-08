"""Shared document-first pipeline. No web framework or external provider imports."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import local
from uuid import uuid4
from .images import decode_pages, Segmenter, png_bytes, enhanced, page_polygon
from .interpretation import Classifier, FieldInterpreter, normalized
from .serialization import content_hash, result_hash, ocr_dict


def values(fields):
    result = {}
    for f in fields:
        if not f["findings"]:
            result.setdefault(f["field"], set()).add(normalized(f["value"]))
    return result


def field_differences(original, improved):
    a, b = values(original), values(improved)
    return [{"field": k, "original_values": sorted(a.get(k, set())),
             "enhanced_values": sorted(b.get(k, set())), "disagreement": a.get(k, set()) != b.get(k, set())}
            for k in sorted(a.keys() | b.keys())]


def completeness(classification, fields, findings):
    kind = classification["type"]
    needed = {"op": ["family_name", "given_name", "birth_date", "document_number"],
              "passport": ["family_name", "given_name", "birth_date", "document_number"],
              "zp": ["family_name", "given_name", "birth_date", "insurance_number", "insurer", "card_number", "expiry_date"]}.get(kind, [])
    available = values(fields)
    missing = [f for f in needed if len(available.get(f, ())) != 1]
    return {"side_coverage": {"front": classification["side"] == "front", "back": classification["side"] == "back"},
            "missing_sides": ["back" if classification["side"] == "front" else "front"] if kind == "op" else [],
            "field_sufficiency": {"required": needed, "missing": missing,
                                  "sufficient": bool(kind) and not missing and not findings},
            "workflow_ready": False, "readiness_reasons": ["human_acceptance_required"] + findings,
            "application_ready": False, "certificate_ready": False}


class SideMatcher:
    def match(self, documents):
        for doc in documents:
            doc["paired_with"] = None
            doc["matching_findings"] = []
        for doc in documents:
            classification = doc["classification"]
            if classification["type"] != "op" or not classification["side"] or doc.get("duplicate_of"):
                continue
            a = values(doc["fields"])
            if len(a.get("document_number", ())) != 1 or any(not f.endswith("_century_unresolved") for f in doc["findings"]):
                continue
            candidates = []
            for other in documents:
                oc = other["classification"]
                if (other is doc or other.get("duplicate_of") or oc["type"] != "op"
                    or oc["country"] != classification["country"] or oc["side"] not in ("front", "back")
                    or oc["side"] == classification["side"]):
                    continue
                b = values(other["fields"])
                if a.get("document_number") != b.get("document_number"):
                    continue
                conflicts = [k for k in ("family_name", "given_name", "birth_date", "expiry_date")
                             if a.get(k) and b.get(k) and a[k] != b[k]]
                mrz = oc.get("mrz")
                if mrz and mrz["valid"]:
                    for key, suffix in (("birth_date", "birth_yymmdd"), ("expiry_date", "expiry_yymmdd")):
                        if a.get(key) and any(v.replace("-", "")[2:] != mrz[suffix] for v in a[key]):
                            conflicts.append(key)
                # Century absence is incomplete evidence, not a contradictory identifier.
                blockers = [f for f in other["findings"] if not f.endswith("_century_unresolved")]
                if conflicts or blockers:
                    doc["matching_findings"].append("identity_evidence_conflict")
                    other["matching_findings"].append("identity_evidence_conflict")
                else:
                    candidates.append(other["document_id"])
            doc["_candidates"] = candidates
        by_id = {d["document_id"]: d for d in documents}
        for doc in documents:
            candidates = doc.get("_candidates", [])
            if len(candidates) == 1:
                other = by_id[candidates[0]]
                if other.get("_candidates") == [doc["document_id"]] and not doc["matching_findings"] and not other["matching_findings"]:
                    doc["paired_with"] = other["document_id"]
                    doc["completeness"]["side_coverage"] = {"front": True, "back": True}
                    doc["completeness"]["missing_sides"] = []
            elif len(candidates) > 1:
                doc["matching_findings"].append("ambiguous_side_match")
        for doc in documents:
            doc.pop("_candidates", None)
        return documents


def associate(doc, workers):
    c = doc["classification"]
    fields = values(doc["fields"])
    identity_field = "card_number" if c["type"] == "zp" else "document_number"
    identifier_type = "ehic_card_number" if c["type"] == "zp" else f"{c['type']}_document_number"
    if len(fields.get(identity_field, ())) != 1 or doc["findings"] or doc["matching_findings"]:
        return {"status": "unassigned", "worker_id": None, "candidates": []}
    candidates = []
    conflicts = False
    for worker in workers:
        for identifier in worker.get("identifiers", []):
            if (identifier.get("type") == identifier_type and identifier.get("issuer") == c["country"]
                and normalized(identifier.get("value", "")) in fields[identity_field]):
                candidates.append(worker["worker_id"])
                identity = worker.get("identity_fields", {})
                if any(fields.get(key) and identity.get(key) and normalized(identity[key]) not in fields[key]
                       for key in ("family_name", "given_name", "birth_date")):
                    conflicts = True
    candidates = sorted(set(candidates), key=str)
    return {"status": "proposed" if len(candidates) == 1 and not conflicts else "ambiguous" if candidates else "unassigned",
            "worker_id": candidates[0] if len(candidates) == 1 and not conflicts else None, "candidates": candidates,
            "findings": ["worker_identity_conflict"] if conflicts else [],
            "accepted": False}


class DocumentProcessor:
    def __init__(self, engine_factory=None):
        self.engine_factory = engine_factory
        self._local = local()

    def _engine(self):
        if not hasattr(self._local, "engine"):
            if self.engine_factory:
                self._local.engine = self.engine_factory()
            else:
                from .adapters.rapidocr import RapidOCRAdapter
                self._local.engine = RapidOCRAdapter()
        return self._local.engine

    def process(self, content, *, workers=(), artifact_sink=None):
        source_hash = content_hash(content)
        documents = []
        for page in decode_pages(content):
            for crop in Segmenter().segment(page):
                original, improved = png_bytes(crop.image), png_bytes(enhanced(crop.image))
                original_hash, enhanced_hash = content_hash(original), content_hash(improved)
                if artifact_sink:
                    artifact_sink(original_hash, original)
                    artifact_sink(enhanced_hash, improved)
                raw = self._engine().process(original)
                enhanced_raw = self._engine().process(improved)
                # Geometry remains tied to the decoded source page for both passes.
                def remap(result):
                    return replace(result, regions=tuple(replace(r, source_page=page.index,
                        polygon=tuple(tuple(p) for p in page_polygon(r.polygon, crop.to_page)),
                        transform="perspective_crop") if r.located else r for r in result.regions))
                raw, enhanced_raw = remap(raw), remap(enhanced_raw)
                classification = Classifier().classify(raw.regions)
                enhanced_classification = Classifier().classify(enhanced_raw.regions)
                fields, findings = FieldInterpreter().interpret(raw.regions, classification)
                improved_fields, improved_findings = FieldInterpreter().interpret(enhanced_raw.regions, enhanced_classification)
                findings += improved_findings
                if (classification["type"], classification["side"]) != (enhanced_classification["type"], enhanced_classification["side"]):
                    findings.append("classification_disagreement")
                diff = field_differences(fields, improved_fields)
                disagreed = {d["field"] for d in diff if d["disagreement"]}
                if disagreed:
                    findings.append("enhancement_disagreement")
                    for field in fields:
                        if field["field"] in disagreed:
                            field["findings"].append("enhancement_disagreement")
                findings.extend(f"{f['field']}:{reason}" for f in fields for reason in f["findings"])
                original_json, enhanced_json = ocr_dict(raw), ocr_dict(enhanced_raw)
                doc = {"document_id": str(uuid4()), "source_hash": source_hash, "source_page": page.index,
                       "polygon": crop.polygon, "crop_to_page": crop.to_page.tolist(),
                       "coordinate_space": "decoded_exif_oriented_page", "page_size": list(page.image.size),
                       "segmentation": {"confidence": crop.confidence, "reason": crop.reason},
                       "classification": classification, "enhanced_classification": enhanced_classification,
                       "fields": fields, "enhanced_fields": improved_fields, "field_diff": diff,
                       "findings": sorted(set(findings)), "ocr": original_json, "enhanced_ocr": enhanced_json,
                       "original_crop_hash": original_hash, "enhanced_crop_hash": enhanced_hash,
                       "provenance": [
                           {"operation": "crop", "input_hash": source_hash, "output_hash": original_hash},
                           {"operation": "enhance_contrast", "input_hash": original_hash, "output_hash": enhanced_hash},
                           {"operation": "ocr_original", "input_hash": original_hash, "output_hash": result_hash(original_json), "engine_version": raw.engine_version},
                           {"operation": "ocr_enhanced", "input_hash": enhanced_hash, "output_hash": result_hash(enhanced_json), "engine_version": enhanced_raw.engine_version}],
                       "worker_id": None}
                doc["completeness"] = completeness(classification, fields, doc["findings"])
                documents.append(doc)
        return self.combine(documents, workers)

    def combine(self, documents, workers=()):
        seen = {}
        for doc in documents:
            doc["duplicate_of"] = seen.get(doc["original_crop_hash"])
            seen.setdefault(doc["original_crop_hash"], doc["document_id"])
        SideMatcher().match(documents)
        for doc in documents:
            doc["association"] = associate(doc, workers)
        return {"schema_version": 1, "documents": documents, "workflow_ready": False}

    def process_batch(self, contents, *, workers=(), max_concurrency=4):
        if not 1 <= max_concurrency <= 4:
            raise ValueError("CONCURRENCY_LIMIT")
        def one(content):
            try:
                return {"status": "completed", "result": self.process(content)}
            except Exception:
                return {"status": "failed", "error_tag": "DOCUMENT_PROCESSING_FAILED", "source_hash": content_hash(content)}
        with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
            runs = list(pool.map(one, contents))
        merged = self.combine([d for run in runs if run["status"] == "completed" for d in run["result"]["documents"]], workers)
        return {**merged, "runs": runs}
