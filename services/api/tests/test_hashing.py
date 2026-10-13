from app.services.hashing import sha256_bytes


def test_sha256_known_value():
    assert sha256_bytes(b"lexi") == "3837436094815981bec3fe499a4f79b520971a9c34594d7d7660ada45c173faf"


def test_sha256_changes_with_content():
    assert sha256_bytes(b"evidencia v1") != sha256_bytes(b"evidencia v2")
