# Release 1A threat model

Synthetic proof scope covers privileged users, compromised sessions, cross-tenant
actors, malicious uploads, duplicate/crashed workers, and mistaken operators.
Trust boundaries are browser/application, application/database, job worker, A1
engine, and protected filesystem/Nginx delivery. Assets are credentials,
membership/authorization state, worker metadata, protected bytes, proposals,
assignments, A1 snapshots/artifacts, and audit evidence.

Mandatory TOTP and credential-version session invalidation mitigate account
abuse. Server-side organization scope mitigates IDOR/tenant leakage. Signature,
MIME, size, traversal, quarantine, and malware gates precede processing. Opaque
keys plus authorized internal redirects prevent direct file serving. Unique
idempotency keys, atomic audit/outbox, versioned payloads, and safe retry mitigate
duplicate delivery and crashes. Non-content append-only audit makes sensitive
reads, denials, reviews, approvals, and transitions attributable.

Residual risks owned before real-data activation: production key management and
filesystem encryption verification (sysadmin), malware engine operations
(sysadmin/product engineering), observed role/terminology exceptions (Jan),
retention/legal basis (privacy owner), and application-consistent restore proof
(sysadmin). None is waived by synthetic proof acceptance.

