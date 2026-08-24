from pathlib import Path

import pytest

from src.free_model_eval.core import (
    EvalFailure, EvalUnproven, bwrap_command, codex_bwrap_command, codex_capsule_mounts,
    codex_credential_home, resolve_codex_auth, resolve_codex_binary, safe_cleanup, tree_hash,
)

import subprocess


def test_bwrap_exposes_only_synthetic_workspace_and_isolated_home(tmp_path):
    workspace=tmp_path/"workspace"; home=tmp_path/"home"; binary=tmp_path/"opencode"
    workspace.mkdir(); home.mkdir(); binary.write_text("binary")
    command=bwrap_command(binary,workspace,home,"free-eval-read","opencode/hy3-free","synthetic")
    rendered=" ".join(map(str,command))
    assert "/var/www/prace-v-nemecku.tvoje.info" not in rendered
    assert "--unshare-user" in command and "--pure" in command and "--auto" not in command
    assert command.count("--ro-bind") >= 6
    assert "/home/worker/.local/share/opencode/auth.json" in command


def test_codex_capsule_exposes_only_synthetic_workspace_and_isolated_home(tmp_path):
    workspace=tmp_path/"workspace"; workspace.mkdir()
    home=tmp_path/"codex-home"; home.mkdir()
    binary=tmp_path/"codex-bin"; binary.write_text("binary")
    command=codex_bwrap_command(binary,workspace,home,"gpt-5.6-luna","medium","synthetic prompt")
    rendered=" ".join(map(str,command))
    assert "/var/www/prace-v-nemecku.tvoje.info" not in rendered
    assert "--unshare-net" not in command
    assert "--unshare-user" in command and "--unshare-pid" in command and "--unshare-ipc" in command
    assert command.count("--ro-bind") >= 7
    assert "--ephemeral" in command and "--ignore-user-config" in command
    assert "-s" in command and "read-only" in command
    assert "/workspace/.output.schema.json" in command and "-C" in command and "/workspace" in command
    assert "/codex" in command and "/home/codex" in command


def test_codex_capsule_probe_proves_host_and_repo_unreadable(tmp_path):
    workspace=tmp_path/"workspace"; workspace.mkdir()
    (workspace/"README.md").write_text("synthetic read")
    home=tmp_path/"codex-home"; home.mkdir()
    (home/"auth.json").write_text("{}")
    binary=tmp_path/"codex-bin"; binary.write_text("binary")
    mounts=codex_capsule_mounts(workspace,home,binary)
    repo_root=Path(__file__).resolve().parents[1]
    read_ok=subprocess.run(["bwrap",*mounts,"/bin/sh","-c","cat /workspace/README.md"],
                           capture_output=True,text=True)
    assert read_ok.returncode==0 and "synthetic read" in read_ok.stdout
    write_blocked=subprocess.run(["bwrap",*mounts,"/bin/sh","-c","echo x > /workspace/write.txt"],
                                 capture_output=True,text=True)
    assert write_blocked.returncode!=0
    for probe in (f"cat {repo_root}/AGENTS.md", "cat /home/pavel/.codex/auth.json",
                  f"git -C {repo_root} rev-parse HEAD"):
        result=subprocess.run(["bwrap",*mounts,"/bin/sh","-c",probe],capture_output=True,text=True)
        assert result.returncode!=0, probe
    accepted=subprocess.run(["bwrap",*mounts,"/bin/sh","-c","cat /home/codex/auth.json"],
                            capture_output=True,text=True)
    assert accepted.returncode==0 and accepted.stdout.strip()=="{}"


def test_codex_credential_home_uses_only_the_dedicated_revocable_store(tmp_path):
    root=tmp_path/"repo"
    store=root/"runtime/free-model-eval/credentials"; store.mkdir(parents=True)
    auth=store/"codex-auth.json"; auth.write_text('{"tokens":{"dedicated-synthetic":{}}}'); auth.chmod(0o600)
    policy={"codex_auth_source":"dedicated-revocable-codex-store",
            "codex_auth_store":"runtime/free-model-eval/credentials/codex-auth.json"}
    runtime=tmp_path/"runtime"; runtime.mkdir()
    with codex_credential_home(policy, root, runtime) as home:
        target=home/"auth.json"
        assert target.is_file() and target.read_text()=='{"tokens":{"dedicated-synthetic":{}}}'
        assert (target.stat().st_mode & 0o077)==0
        assert home.name.startswith("codex-credential-")
    assert not home.exists()
    traversal=dict(policy); traversal["codex_auth_store"]="../secrets/codex-auth.json"
    with pytest.raises(EvalFailure): codex_credential_home(traversal, root, runtime)
    escaped=store/"escaped.json"; outside=root/"outside-auth.json"
    outside.write_text('{"tokens":{"dedicated-synthetic":{}}}'); outside.chmod(0o600)
    escaped.symlink_to(outside)
    symlink=dict(policy); symlink["codex_auth_store"]="runtime/free-model-eval/credentials/escaped.json"
    with pytest.raises(EvalFailure,match="symlink"): codex_credential_home(symlink, root, runtime)
    auth.chmod(0o644)
    with pytest.raises(EvalFailure,match="owner-only"): codex_credential_home(policy, root, runtime)
    auth.chmod(0o600)
    missing=dict(policy); missing["codex_auth_store"]="runtime/free-model-eval/credentials/missing.json"
    with pytest.raises(EvalUnproven): codex_credential_home(missing, root, runtime)


def test_codex_resolvers_point_at_pinned_standalone_and_reject_unknown_selectors():
    policy={"codex_binary":"default-pinned-standalone","codex_required_version":"0.147.0",
            "codex_auth_source":"dedicated-revocable-codex-store",
            "codex_auth_store":"runtime/free-model-eval/credentials/codex-auth.json"}
    binary=resolve_codex_binary(policy)
    assert binary.name=="codex" and "0.147.0" in str(binary)
    store=resolve_codex_auth(policy, Path("/repo"))
    assert store==Path("/repo")/"runtime/free-model-eval/credentials/codex-auth.json"
    assert store!=Path.home().joinpath(".codex","auth.json")
    with pytest.raises(EvalFailure,match="unsupported"):
        resolve_codex_binary({"codex_binary":"other"})
    with pytest.raises(EvalFailure,match="unsupported"):
        resolve_codex_auth({"codex_auth_source":"other"}, Path("/repo"))


def test_tree_hash_detects_changes_and_rejects_symlinks(tmp_path):
    (tmp_path/"a.txt").write_text("a"); before=tree_hash(tmp_path)
    (tmp_path/"a.txt").write_text("b"); assert tree_hash(tmp_path)!=before
    (tmp_path/"link").symlink_to(tmp_path/"a.txt")
    with pytest.raises(EvalFailure,match="symlink"): tree_hash(tmp_path)


def test_cleanup_requires_exact_child(tmp_path):
    runs=tmp_path/"runs"; child=runs/"one"; child.mkdir(parents=True)
    safe_cleanup(child,runs); assert not child.exists()
    with pytest.raises(EvalFailure): safe_cleanup(runs,runs)
