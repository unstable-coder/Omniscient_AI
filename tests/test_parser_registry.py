from app.parsers.parser_registry import get_parser_for_file


def test_parser_selection_known_extension() -> None:
    parser = get_parser_for_file("example.pdf")
    assert parser is not None
    assert parser.__class__.__name__ == "PDFParser"


def test_parser_selection_unknown_extension() -> None:
    parser = get_parser_for_file("unknown.bin")
    assert parser is None
