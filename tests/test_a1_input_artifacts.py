"""Synthetic input-bundle publication; no source employee inputs."""
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import pytest
from portal.release1a.input_artifacts import publish_input_artifact
from portal.release1a.j4_artifacts import ArtifactError


def payloads():
    result = {'review.csv': b'employee_id\nsynthetic-1\n', 'cohort.json': b'[]',
              'employees_normalized.json': b'[]', 'input_snapshots.json': b'{}',
              'profiles/synthetic-office.json': b'{"synthetic":true}'}
    result['manifest.json'] = json.dumps({'payload_sha256': {
        name: hashlib.sha256(data).hexdigest() for name, data in result.items()}}).encode()
    return result


def test_retry_preserves_exact_private_bundle(tmp_path):
    data = payloads()
    reference = publish_input_artifact(tmp_path, data)
    assert publish_input_artifact(tmp_path, data) == reference
    folder = tmp_path / reference['relative_path']
    assert folder.name == hashlib.sha256(data['manifest.json']).hexdigest()
    assert folder.stat().st_mode & 0o777 == 0o700
    for name, expected in data.items():
        assert (folder / name).read_bytes() == expected
        assert (folder / name).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('change', ['hash', 'missing', 'traversal', 'extra'])
def test_invalid_inputs_rejected_before_storage(tmp_path, change):
    root = tmp_path / 'not-created'
    data = payloads()
    if change == 'hash': data['review.csv'] += b'changed'
    elif change == 'missing': del data['cohort.json']
    elif change == 'traversal': data['profiles/../secret.json'] = b'{}'
    else: data['unexpected.json'] = b'{}'
    with pytest.raises(ArtifactError): publish_input_artifact(root, data)
    assert not root.exists()


@pytest.mark.parametrize('change', ['bytes', 'missing', 'extra', 'mode', 'symlink', 'directory'])
def test_existing_bundle_tamper_never_overwritten(tmp_path, change):
    data = payloads()
    reference = publish_input_artifact(tmp_path, data)
    folder = tmp_path / reference['relative_path']
    selected = folder / 'review.csv'
    if change == 'bytes': selected.write_bytes(b'tampered')
    elif change == 'missing': selected.unlink()
    elif change == 'extra': (folder / 'extra').write_bytes(b'x')
    elif change == 'mode': selected.chmod(0o644)
    elif change == 'directory': (folder / 'unexpected').mkdir(mode=0o700)
    else:
        selected.unlink()
        selected.symlink_to(folder / 'cohort.json')
    with pytest.raises(ArtifactError): publish_input_artifact(tmp_path, data)
    if change == 'bytes': assert selected.read_bytes() == b'tampered'
    assert not list((tmp_path / 'a1-input').glob('.stage-*'))


def test_symlink_and_unsafe_root_rejected(tmp_path):
    unsafe = tmp_path / 'unsafe'
    unsafe.mkdir(mode=0o755)
    unsafe.chmod(0o755)  # Test the actual mode independently of the invoking umask.
    with pytest.raises(ArtifactError): publish_input_artifact(unsafe, payloads())
    link = tmp_path / 'link'
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ArtifactError): publish_input_artifact(link, payloads())


def test_write_failure_cleans_unpublished_stage(tmp_path):
    with patch('portal.release1a.input_artifacts._write', side_effect=OSError('synthetic disk failure')):
        with pytest.raises(OSError): publish_input_artifact(tmp_path, payloads())
    assert list((tmp_path / 'a1-input').iterdir()) == [tmp_path / 'a1-input/.publication.lock']
    publish_input_artifact(tmp_path, payloads())


def test_concurrent_retry_publishes_one_bundle(tmp_path):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: publish_input_artifact(tmp_path, payloads()), range(2)))
    assert results[0] == results[1]
    assert len(list((tmp_path / 'a1-input').iterdir())) == 2


def test_swap_to_symlink_between_mode_check_and_open_rejected(tmp_path):
    from portal.release1a import input_artifacts
    data = payloads()
    reference = publish_input_artifact(tmp_path, data)
    selected = tmp_path / reference['relative_path'] / 'review.csv'
    original_mode = input_artifacts._mode
    def swap(path, expected):
        original_mode(path, expected)
        if path == selected:
            path.unlink()
            path.symlink_to(path.parent / 'cohort.json')
    with patch.object(input_artifacts, '_mode', side_effect=swap):
        with pytest.raises((ArtifactError, OSError)):
            publish_input_artifact(tmp_path, data)
    assert selected.is_symlink()


def test_canonical_hyphen_slug_supported(tmp_path):
    data = payloads()
    data['profiles/-synthetic--office-.json'] = data.pop('profiles/synthetic-office.json')
    data['manifest.json'] = json.dumps({'payload_sha256': {
        name: hashlib.sha256(value).hexdigest() for name, value in data.items()
        if name != 'manifest.json'}}).encode()
    publish_input_artifact(tmp_path, data)


def test_validation_binds_snapshot_before_caller_mutation(tmp_path):
    from portal.release1a import input_artifacts
    data = payloads()
    expected = dict(data)
    validate = input_artifacts._validate
    def mutate(snapshot):
        assert snapshot is not data
        data['review.csv'] = b'concurrent caller mutation'
        return validate(snapshot)
    with patch.object(input_artifacts, '_validate', side_effect=mutate):
        reference = publish_input_artifact(tmp_path, data)
    assert (tmp_path / reference['relative_path'] / 'review.csv').read_bytes() == expected['review.csv']
