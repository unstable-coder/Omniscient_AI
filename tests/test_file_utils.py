from app.utils.file_utils import sanitize_filename


def test_sanitize_filename_removes_bad_characters() -> None:
    assert sanitize_filename("../secret.txt") == "secret.txt"
    assert sanitize_filename("some file@name!.pdf") == "some_file_name.pdf"
