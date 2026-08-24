from prototypes.architecture.adr001.proof_contract import AuditEvent, AuditLog, IdempotentJobs

def test_atomic_command_shape_and_safe_concurrent_retry():
    jobs, audit = IdempotentJobs(), AuditLog()
    result = jobs.execute("assignment:worker-synth:v1", {"version": 1})
    audit.append(AuditEvent("status_transition", "user-synth", "org-alpha", result["key"], "success"))
    duplicate = jobs.execute("assignment:worker-synth:v1", {"version": 1})
    assert duplicate == result and len(jobs.effects) == len(audit.events) == 1

