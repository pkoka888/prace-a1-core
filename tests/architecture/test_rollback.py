def test_version_skew_and_forward_fix_contract():
    compatibility = {"release_previous": [1], "release_current": [1, 2], "worker_current": [1, 2]}
    assert set(compatibility["release_previous"]) <= set(compatibility["release_current"])
    assert set(compatibility["worker_current"]) == set(compatibility["release_current"])
    migrations = [{"name": "add_nullable_activity_profile", "classification": "reversible"}]
    assert all(m["classification"] in {"reversible", "forward-fix-approved"} for m in migrations)
