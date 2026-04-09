from __future__ import annotations

import argparse
import json

from src.docx_io.semantic_diagnostics import analyze_docx


def _human_lines(report: dict[str, object]) -> list[str]:
    lines = [f"File: {report['path']}"]
    if not report.get("exists"):
        lines.append("  status: missing")
        return lines
    if not report.get("zip_ok"):
        lines.append(f"  status: {report.get('error', 'zip_error')}")
        return lines

    body = report["document_body"]
    lines.append("  status: zip/xml readable")
    lines.append(
        f"  body: last_child={body['last_child']}, sectPr_last={body['sectpr_is_last']}, direct_sectPr={body['direct_sectpr_count']}"
    )
    if report["required_parts_missing"]:
        lines.append(f"  missing_parts: {report['required_parts_missing']}")
    if report["xml_parse_errors"]:
        lines.append(f"  xml_parse_errors: {len(report['xml_parse_errors'])}")
    if report["document_relationship_missing_targets"]:
        lines.append(
            f"  broken_document_relationships: {len(report['document_relationship_missing_targets'])}"
        )
    if report["dangling_rids_in_document"]:
        lines.append(f"  dangling_rids_in_document: {report['dangling_rids_in_document']}")

    for range_name, stats in report["ranges"].items():
        if stats["orphan_start_ids"] or stats["orphan_end_ids"]:
            lines.append(
                f"  {range_name}: orphan_start_ids={stats['orphan_start_ids']}, orphan_end_ids={stats['orphan_end_ids']}"
            )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only DOCX semantic diagnostics for broken range markers and relationship issues.",
    )
    parser.add_argument("paths", nargs="+", help="DOCX files to analyze")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    reports = [analyze_docx(path) for path in args.paths]
    payload = {"files": reports}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for index, report in enumerate(reports):
            if index:
                print()
            for line in _human_lines(report):
                print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
