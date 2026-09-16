"""Browser-wait guard; missing source or a scan error cannot pass."""
from scripts.validate_delivery_readiness import scan_browser_waits


def test_no_networkidle_in_automation():
    result = scan_browser_waits()
    assert result["status"] == "passed", result
