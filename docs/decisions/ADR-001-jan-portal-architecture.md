# ADR-001 — Jan Portal Architecture

**Status:** proposed
**Owner:** product engineering
**Approver:** Pavel
**Milestone:** M1A

## Context

Release 1A needs one measured architecture for protected worker documents, OCR
proposals, assignments, A1 cases, audit, and organization-scoped authorization.

## Proposed default

Django 5.2 LTS on Python 3.13 as a modular monolith with PostgreSQL, Django
templates plus targeted HTMX, a background worker, protected filesystem storage,
and the existing A1 engine behind a Django-independent Python interface.

## Required evidence before acceptance

Plan E must attach reproducible synthetic proof results, threat model, selected
versions/licenses, weighted comparison and sensitivity results, application
observability, deployment rollback proof, dependency review, and unresolved risks.
MFA, queue, storage, and audit choices remain open until those proofs pass.

## Decision

Pending. Update this ADR with selected packages, topology, trust/data boundaries,
alternatives, consequences, upgrade/rollback path, evidence links, approval, and
date. The proposed default is not authorization to scaffold or deploy.
