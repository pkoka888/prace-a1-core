# ADR-001 proof report

The executable source is under `prototypes/architecture/adr001/`; the eight
focused proof files exercise MFA, tenant isolation, jobs/transactions, protected
storage, audit, the A1 boundary, dependencies, and rollback. `run` writes a
hash-bound manifest and receipt; `verify` fails if required checks or source
hashes differ.

The selected modular monolith retains the declared weighted recommendation under
normal, doubled-security, and doubled-speed/cost sensitivities because it avoids
an additional API/frontend and Redis service while preserving replaceable
boundaries. Synthetic measurements do not claim production capacity, encryption
at rest, malware operations, or host recovery evidence; those remain Plan K and
real-data activation gates.
