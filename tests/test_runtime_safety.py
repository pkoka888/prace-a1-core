"""Runtime access contracts on new synthetic filesystem trees only."""

import os

import pytest

from portal.release1a import runtime_safety


@pytest.fixture
def runtime_root(tmp_path, monkeypatch):
    checkout = tmp_path / "synthetic-checkout"
    monkeypatch.setattr(runtime_safety, "__file__",
                        str(checkout / "portal/release1a/runtime_safety.py"))
    root = checkout / "runtime/portal/supervised-fixture"
    root.mkdir(parents=True)
    os.chown(root, -1, os.getegid())
    root.chmod(0o700)
    return root


@pytest.mark.parametrize("mode,accepted", [
    (0o700, True), (0o2700, True), (0o750, True), (0o2750, True),
    (0o770, False), (0o755, False), (0o705, False), (0o500, False),
])
def test_runtime_root_access_bits(runtime_root, mode, accepted):
    runtime_root.chmod(mode)
    if accepted:
        assert runtime_safety.confined_root(runtime_root) == runtime_root
    else:
        with pytest.raises(ValueError, match="RUNTIME_ROOT_PERMISSIONS"):
            runtime_safety.confined_root(runtime_root)
    assert runtime_root.stat().st_mode & 0o7777 == mode


def test_group_readable_root_requires_effective_primary_gid(runtime_root, monkeypatch):
    runtime_root.chmod(0o750)
    monkeypatch.setattr(runtime_safety.os, "getegid", lambda: runtime_root.stat().st_gid + 1)
    with pytest.raises(ValueError, match="RUNTIME_ROOT_PERMISSIONS"):
        runtime_safety.confined_root(runtime_root)
    # A differing group carries no access under the owner-only default.
    runtime_root.chmod(0o2700)
    assert runtime_safety.confined_root(runtime_root) == runtime_root


def test_missing_root_preserves_permission_error_contract(runtime_root):
    runtime_root.rmdir()
    with pytest.raises(ValueError, match="RUNTIME_ROOT_PERMISSIONS"):
        runtime_safety.confined_root(runtime_root)


def test_static_group_permission_does_not_apply_to_private_directory(runtime_root, monkeypatch):
    child = runtime_root / "synthetic-child"
    child.mkdir()
    os.chown(child, -1, os.getegid())
    child.chmod(0o750)
    assert runtime_safety.runtime_directory(child, allow_static_group=True) == child
    with pytest.raises(ValueError, match="RUNTIME_DIRECTORY_PERMISSIONS"):
        runtime_safety.runtime_directory(child)
    monkeypatch.setattr(runtime_safety.os, "getegid", lambda: child.stat().st_gid + 1)
    with pytest.raises(ValueError, match="RUNTIME_DIRECTORY_PERMISSIONS"):
        runtime_safety.runtime_directory(child, allow_static_group=True)


def test_directory_guard_preserves_owner_type_and_symlink_checks(runtime_root, monkeypatch):
    file = runtime_root / "synthetic-file"
    file.write_text("synthetic")
    file.chmod(0o700)
    with pytest.raises(ValueError, match="RUNTIME_DIRECTORY_PERMISSIONS"):
        runtime_safety.runtime_directory(file)
    linked = runtime_root / "synthetic-link"
    linked.symlink_to(runtime_root, target_is_directory=True)
    with pytest.raises(ValueError, match="PATH_SYMLINK"):
        runtime_safety.runtime_directory(linked)
    monkeypatch.setattr(runtime_safety.os, "getuid", lambda: runtime_root.stat().st_uid + 1)
    with pytest.raises(ValueError, match="RUNTIME_DIRECTORY_PERMISSIONS"):
        runtime_safety.runtime_directory(runtime_root)
