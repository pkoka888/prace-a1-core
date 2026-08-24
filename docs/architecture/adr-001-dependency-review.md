# ADR-001 dependency and recoverability review

The synthetic baseline pins Django 5.2.17, django-allauth 65.19.1,
django-q2 1.11.0, psycopg 3.3.4, and cryptography 50.0.0 on Python 3.13.
The proof runner records the exact requirements hash and runtime environment.
Selected components remain replaceable behind authentication, job, storage, and
A1 boundaries. Production vulnerability review must be repeated at release time.

Rollback uses expand/migrate/contract migrations, versioned job payloads, paused
consumers during incompatible transitions, artifact/source hashes, database plus
protected-file backup consistency, and a 15-minute synthetic restore/forward-fix
target. Irreversible migrations cannot enter a release without an accepted
forward-fix. Application logs and metrics expose event types, opaque IDs,
durations, queue depth, retry counts, and outcomes only—never document content or
identity values.

