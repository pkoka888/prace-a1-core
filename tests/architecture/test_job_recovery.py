import pytest
from prototypes.architecture.adr001.proof_contract import IdempotentJobs

def test_retry_timeout_duplicate_and_crash_have_one_effect():
    jobs = IdempotentJobs()
    with pytest.raises(TimeoutError): jobs.execute("ocr:synthetic-1", {"document": "doc-synth"}, True)
    first = jobs.execute("ocr:synthetic-1", {"document": "doc-synth"})
    assert jobs.execute("ocr:synthetic-1", {"document": "doc-synth"}) == first
    assert len(jobs.effects) == 1 and jobs.attempts["ocr:synthetic-1"] == 3

