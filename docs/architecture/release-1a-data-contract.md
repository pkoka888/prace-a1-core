# Release 1A minimum data and transaction contract

**Status:** accepted for the synthetic M2 prototype; real-data activation remains blocked.

Every tenant-owned row has a non-null `organization_id`; authorization begins
from an active, effective-dated membership and never from a client-supplied
organization identifier. `Person`, `Worker`, and authentication `User` remain
distinct. Files use opaque keys outside static/media serving and are delivered
only after server-side authorization through an internal redirect.

Writes use atomic command boundaries with optimistic `version` checks. OCR and
A1 jobs have unique idempotency keys, durable state, retry counters, compatible
payload versions, and transactional audit/outbox insertion. Assignment overlap
is retained as a visible warning but blocks A1 readiness where the requested
period is ambiguous. A1 artifacts bind to immutable source hashes and become
stale after a source change; `prepared` and `official` are distinct states.

Audit events contain actor, organization, event type, opaque object reference,
outcome, and time—never document bytes, extracted identity values, credentials,
or form payloads. Deletion revokes access first, records a tombstone/audit event,
then purges derived proposals and protected bytes under the retention/legal-hold
policy. Append-only audit and legally required evidence follow their separate
retention rules.

Migrations are expand/migrate/contract: additive nullable/schema-compatible
changes first, version-skew-safe workers during rollout, reconciled backfill,
then constraint tightening. Destructive/irreversible changes require an accepted
forward-fix plan and restore evidence. Required indexes cover organization plus
natural lookup/version, worker assignment periods, document hash/state, job
state/availability/idempotency key, and A1 worker/source hash.

