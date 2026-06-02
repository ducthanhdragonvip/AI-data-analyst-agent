from pathlib import Path


def remove_uploaded_file(upload_dir: Path, file_name: str | None) -> bool:
    if not file_name:
        return False

    upload_root = upload_dir.resolve()
    target = (upload_root / file_name).resolve()
    if upload_root not in target.parents and target != upload_root:
        return False
    if not target.exists() or not target.is_file():
        return False
    target.unlink()
    return True
