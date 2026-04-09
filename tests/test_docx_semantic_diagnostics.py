import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "_diagnose_docx_semantics.py"


def _run_script(*paths: Path):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *[str(path) for path in paths]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        check=False,
    )
    return completed


def _sample(pattern: str) -> Path:
    matches = sorted(ROOT.glob(pattern))
    assert matches, f"No files matched {pattern!r}"
    return matches[0]


def test_diagnostic_script_flags_orphan_bookmark_end_on_known_sample():
    suspect = _sample("tests/00/*20260310_new.docx")

    result = _run_script(suspect)

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert len(payload["files"]) == 1
    report = payload["files"][0]
    assert report["zip_ok"] is True
    assert "191" in report["ranges"]["bookmark"]["orphan_end_ids"]


def test_diagnostic_script_reports_clean_bookmark_ranges_on_known_good_sample():
    good = _sample("tests/00/*分类号_new.docx")

    result = _run_script(good)

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    report = payload["files"][0]
    assert report["zip_ok"] is True
    assert report["ranges"]["bookmark"]["orphan_end_ids"] == []
    assert report["ranges"]["bookmark"]["orphan_start_ids"] == []
