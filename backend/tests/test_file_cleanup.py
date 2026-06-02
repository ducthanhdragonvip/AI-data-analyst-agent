from pathlib import Path

from app.services.file_cleanup import remove_uploaded_file


def test_remove_uploaded_file_deletes_file_inside_upload_dir(tmp_path: Path) -> None:
    upload = tmp_path / "sales.csv"
    upload.write_text("region,revenue\nWest,100\n", encoding="utf-8")

    assert remove_uploaded_file(tmp_path, "sales.csv") is True
    assert not upload.exists()


def test_remove_uploaded_file_rejects_path_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.csv"
    outside.write_text("region,revenue\nWest,100\n", encoding="utf-8")

    assert remove_uploaded_file(tmp_path, "../outside.csv") is False
    assert outside.exists()
    outside.unlink()
