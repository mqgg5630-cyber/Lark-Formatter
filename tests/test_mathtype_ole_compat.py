import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "formula_core" / "mathtype_ole.py"


def test_mathtype_ole_source_parses_with_python311_grammar():
    source = SOURCE.read_text(encoding="utf-8")

    tree = ast.parse(source, filename=str(SOURCE), feature_version=11)

    assert tree is not None


def test_mathtype_ole_matrix_row_separator_matches_previous_output():
    row_separator = r" \\ "
    rows = ["a & b", "c & d"]

    previous = r"\begin{matrix}" + " \\\\ ".join(rows) + r"\end{matrix}"
    current = rf"\begin{{matrix}}{row_separator.join(rows)}\end{{matrix}}"

    assert current == previous
