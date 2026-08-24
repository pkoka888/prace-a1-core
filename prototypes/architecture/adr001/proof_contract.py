"""Disposable, synthetic-only behavior used by ADR-001 architecture proofs."""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import secrets
import struct
import time
from dataclasses import dataclass, field
from pathlib import PurePosixPath


class Denied(Exception): pass
class InvalidUpload(Exception): pass


def totp(secret: bytes, at: int, step: int = 30) -> str:
    counter = struct.pack(">Q", at // step)
    digest = hmac.new(secret, counter, hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff
    return f"{value % 1_000_000:06d}"


@dataclass
class Session:
    user_id: str
    privileged: bool
    credential_version: int
    mfa_at: int | None = None

    def authorize(self, current_version: int) -> None:
        if current_version != self.credential_version or (self.privileged and self.mfa_at is None):
            raise Denied("fresh mandatory MFA required")


@dataclass
class RecoveryCodes:
    hashes: set[str]

    @classmethod
    def issue(cls, codes: list[str]) -> "RecoveryCodes":
        return cls({hashlib.sha256(c.encode()).hexdigest() for c in codes})

    def use(self, code: str) -> bool:
        digest = hashlib.sha256(code.encode()).hexdigest()
        if digest not in self.hashes:
            return False
        self.hashes.remove(digest)
        return True


def scoped(rows: list[dict], organization_id: str) -> list[dict]:
    return [row for row in rows if row["organization_id"] == organization_id]


def require_scope(actor_org: str, object_org: str) -> None:
    if actor_org != object_org:
        raise Denied("organization boundary")


@dataclass(frozen=True)
class StoredDocument:
    organization_id: str
    object_key: str
    sha256: str
    content_type: str
    size: int


def validate_upload(organization_id: str, filename: str, claimed_type: str, content: bytes, limit: int = 4096) -> StoredDocument:
    suffix = PurePosixPath(filename).suffix.lower()
    signatures = {".pdf": ("application/pdf", b"%PDF-"), ".png": ("image/png", b"\x89PNG\r\n\x1a\n")}
    if "/" in filename or "\\" in filename or suffix not in signatures or len(content) > limit:
        raise InvalidUpload("path, type, or size rejected")
    expected_type, magic = signatures[suffix]
    if claimed_type != expected_type or not content.startswith(magic):
        raise InvalidUpload("content signature mismatch")
    digest = hashlib.sha256(content).hexdigest()
    return StoredDocument(organization_id, f"objects/{digest[:2]}/{secrets.token_hex(16)}", digest, expected_type, len(content))


def download_headers(actor_org: str, document: StoredDocument) -> dict[str, str]:
    require_scope(actor_org, document.organization_id)
    return {"X-Accel-Redirect": f"/_protected/{document.object_key}", "Content-Type": document.content_type}


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor_id: str
    organization_id: str
    object_ref: str
    outcome: str


class AuditLog:
    def __init__(self): self._events: list[AuditEvent] = []
    def append(self, event: AuditEvent) -> None: self._events.append(event)
    @property
    def events(self) -> tuple[AuditEvent, ...]: return tuple(self._events)


@dataclass
class IdempotentJobs:
    effects: dict[str, dict] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)

    def execute(self, key: str, payload: dict, fail_before_commit: bool = False) -> dict:
        self.attempts[key] = self.attempts.get(key, 0) + 1
        if key in self.effects: return self.effects[key]
        result = {"key": key, "payload_hash": stable_hash(payload), "status": "committed"}
        if fail_before_commit: raise TimeoutError("synthetic injected crash")
        self.effects[key] = result
        return result


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def a1_prepare(profile: dict, assignments: list[dict], previous_source_hash: str | None = None) -> dict:
    required = {"given_name", "family_name", "birth_date", "activity_profile"}
    missing = sorted(required - profile.keys())
    overlaps = any(a["start"] <= b["end"] and b["start"] <= a["end"] for i, a in enumerate(assignments) for b in assignments[i + 1:])
    source_hash = stable_hash({"profile": profile, "assignments": assignments})
    ready = not missing and not overlaps
    return {"ready": ready, "missing": missing, "ambiguous_assignment": overlaps, "source_hash": source_hash,
            "artifact_hash": stable_hash({"source_hash": source_hash, "kind": "prepared"}) if ready else None,
            "stale": previous_source_hash not in (None, source_hash), "status": "prepared" if ready else "blocked", "official": False}

