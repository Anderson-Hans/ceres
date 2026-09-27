import shutil

from ceres.preflight.spec import SPEC_PATH, SPEC_SHA256, sha256_file, verify_spec


def test_source_spec_unchanged(root):
    ok, msg = verify_spec(root)
    assert ok, msg
    assert sha256_file(root / SPEC_PATH) == SPEC_SHA256


def test_tampered_spec_detected(tmp_path, root):
    dst = tmp_path / SPEC_PATH
    dst.parent.mkdir(parents=True)
    shutil.copy(root / SPEC_PATH, dst)
    with open(dst, "a", encoding="utf-8") as f:
        f.write("\n")
    ok, msg = verify_spec(tmp_path)
    assert not ok and "mismatch" in msg


def test_missing_spec_detected(tmp_path):
    ok, msg = verify_spec(tmp_path)
    assert not ok and "missing" in msg
