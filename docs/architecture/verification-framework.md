# Verification Framework

## Principle: Every automated task needs independent verification

```
┌─────────────────────────────────────────────────────────────────┐
│  Primary Workflow                                           │
│  - Main implementation                                     │
│  - Produces output                                         │
└─────────────────────────────────────────────────────────────────┘
        │
        │ (run in parallel)
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Verification Workflow                                       │
│  - Independent implementation                               │
│  - Same goal, different approach                           │
│  - Cross-validates output                                  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  External Validation                                        │
│  - Web search for existing solutions                        │
│  - Git repos verification                                   │
│  - Authoritative source check                               │
└─────────────────────────────────────────────────────────────────┘
```

## Verification Types

| Type | Purpose | When |
|------|---------|------|
| **Dual Framework** | Same task, different implementation | All automated tasks |
| **Web Search** | Verify against existing solutions | Research/institution data |
| **Git Verification** | Check for existing implementations | Code generation |
| **Source Cross-ref** | Verify against authoritative source | Data validation |
| **Template Match** | Ensure output matches expected format | PDF/document generation |

## Dual Framework Pattern

```python
def verify_with_dual_framework(task: str, primary_fn, secondary_fn) -> VerificationResult:
    """
    Run same task with two different approaches, compare results.
    """
    # Run both in parallel
    primary_result = primary_fn(task)
    secondary_result = secondary_fn(task)
    
    # Compare outputs
    differences = compare_results(primary_result, secondary_result)
    
    # Report discrepancies
    if differences:
        return VerificationResult(
            status="DISCREPANCY",
            differences=differences,
            primary=primary_result,
            secondary=secondary_result
        )
    
    return VerificationResult(status="VERIFIED")
```

## Verification Checklist

For each automated task, verify:

- [ ] **No hardcoded values** - All values come from config/environment
- [ ] **Cross-framework match** - Two implementations produce same result
- [ ] **Web exists** - Solution or similar exists on web
- [ ] **Git verified** - Not inventing new pattern
- [ ] **Authoritative source** - Data from official source
- [ ] **No hallucinations** - Output matches input data
- [ ] **Schema validated** - Output matches expected schema

## A1 Generation Verification

```python
# verify_a1_generation.py
"""
Verify A1 PDF generation with multiple approaches.
"""
from typing import TypedDict

class A1VerificationResult(TypedDict):
    framework_1_matches_template: bool
    framework_2_matches_template: bool
    both_frameworks_match: bool
    no_hardcoded_fields: bool
    fields_from_config: bool

def verify_a1_generation(worker_id: str) -> A1VerificationResult:
    # 1. Generate with Framework 1 (overlay)
    pdf1 = generate_with_overlay(worker_id)
    
    # 2. Generate with Framework 2 (placeholder)
    pdf2 = generate_with_placeholder(worker_id)
    
    # 3. Verify both match
    match = pdf1.pages == pdf2.pages
    
    # 4. Verify no hardcoded values
    no_hardcodes = check_no_hardcodes(pdf1, config)
    
    # 5. Verify fields come from config
    from_config = verify_fields_from_config(pdf1, employee_data)
    
    return A1VerificationResult(
        framework_1_matches_template=True,
        framework_2_matches_template=True,
        both_frameworks_match=match,
        no_hardcoded_fields=no_hardcodes,
        fields_from_config=from_config
    )
```

## OSSZ Verification

```python
# verify_ossz_research.py
"""
Verify OSSZ institution data with multiple sources.
"""
def verify_ossz_research(institution_id: str) -> VerificationResult:
    # 1. Web search for CSSZ contacts
    web_results = search_cssz_contacts(institution_id)
    
    # 2. Check existing git repos for solutions
    git_results = search_repos_for_ossz_solutions()
    
    # 3. Verify against authoritative source (CSSZ website)
    official_data = fetch_from_cssz(institution_id)
    
    # 4. Cross-reference all sources
    verified = cross_reference(web_results, git_results, official_data)
    
    return verified
```

## Cross-Validation Rules

| Check | Pass | Fail |
|-------|------|------|
| Dual framework match | Outputs identical | Discrepancy found |
| Web search | Solution exists | Novel/unverified |
| Git verification | Pattern found | Invented pattern |
| Hardcode check | No hardcoded values | Hardcoded found |
| Schema validation | Output valid | Schema mismatch |
| Source verification | From authoritative source | Unverified source |

## File structure

```
verification/
├── __init__.py
├── dual_framework.py        # Two-implementation comparison
├── web_search.py           # External solution verification
├── git_verification.py     # Git repo pattern check
├── schema_validator.py     # Output schema validation
├── hardcode_checker.py    # No hardcoded values check
└── cross_reference.py      # Multi-source verification
```

## CI Integration

```yaml
# .github/verify.yml
name: Verification Pipeline
on: [push]

jobs:
  verify-a1-generation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Dual Framework Verification
        run: |
          python verification/dual_framework.py --task a1-generation
      
      - name: Web Search Verification
        run: |
          python verification/web_search.py --query "Czech A1 certificate PDF generator"
      
      - name: Git Repo Check
        run: |
          python verification/git_verification.py --pattern a1-pdf
```

This framework ensures every automated task is properly verified before deployment.
