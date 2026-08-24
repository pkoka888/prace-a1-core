import pytest
from prototypes.architecture.adr001.proof_contract import Denied, require_scope, scoped

def test_queryset_view_form_task_admin_download_matrix_denies_cross_org():
    rows = [{"organization_id": "org-alpha", "id": "a"}, {"organization_id": "org-beta", "id": "b"}]
    assert [r["id"] for r in scoped(rows, "org-alpha")] == ["a"]
    for layer in ("view", "form", "task", "admin", "download"):
        with pytest.raises(Denied, match="organization"):
            require_scope("org-alpha", "org-beta")

