from __future__ import annotations

import posixpath
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

RANGE_TAGS = {
    "bookmark": ("bookmarkStart", "bookmarkEnd"),
    "comment": ("commentRangeStart", "commentRangeEnd"),
    "move_from": ("moveFromRangeStart", "moveFromRangeEnd"),
    "move_to": ("moveToRangeStart", "moveToRangeEnd"),
    "custom_xml_ins": ("customXmlInsRangeStart", "customXmlInsRangeEnd"),
    "custom_xml_del": ("customXmlDelRangeStart", "customXmlDelRangeEnd"),
    "custom_xml_move_from": ("customXmlMoveFromRangeStart", "customXmlMoveFromRangeEnd"),
    "custom_xml_move_to": ("customXmlMoveToRangeStart", "customXmlMoveToRangeEnd"),
    "permission": ("permStart", "permEnd"),
}


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _word_xml_parts(names: set[str]) -> list[str]:
    return [
        name
        for name in sorted(names)
        if name.startswith("word/") and name.endswith(".xml") and "/_rels/" not in name
    ]


def _story_parts(names: set[str]) -> list[str]:
    selected: list[str] = []
    for name in _word_xml_parts(names):
        if name in {
            "word/document.xml",
            "word/comments.xml",
            "word/footnotes.xml",
            "word/endnotes.xml",
            "word/glossary/document.xml",
        }:
            selected.append(name)
        elif name.startswith("word/header") or name.startswith("word/footer"):
            selected.append(name)
    return selected


def _source_part_from_rels(rels_name: str) -> str:
    rels_path = PurePosixPath(rels_name)
    if rels_path.name == ".rels":
        return ""
    rels_dir = rels_path.parent
    if rels_dir.name != "_rels":
        return ""
    source_dir = rels_dir.parent
    source_name = rels_path.name[:-5]
    return str((source_dir / source_name)).lstrip("./")


def _resolve_rel_target(rels_name: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    source_part = _source_part_from_rels(rels_name)
    base_dir = posixpath.dirname(source_part)
    if not base_dir:
        return posixpath.normpath(target)
    return posixpath.normpath(posixpath.join(base_dir, target))


def _read_xml(zf: zipfile.ZipFile, name: str):
    return etree.fromstring(zf.read(name))


def _body_summary(root) -> dict[str, object]:
    body = root.find(_w("body"))
    if body is None:
        return {"last_child": None, "sectpr_is_last": False, "direct_sectpr_count": 0}
    children = list(body)
    last_child = etree.QName(children[-1]).localname if children else None
    return {
        "last_child": last_child,
        "sectpr_is_last": last_child == "sectPr",
        "direct_sectpr_count": sum(
            1 for child in children if etree.QName(child).localname == "sectPr"
        ),
    }


def _empty_range_aggregate() -> dict[str, dict[str, object]]:
    return {
        name: {
            "start_count": 0,
            "end_count": 0,
            "orphan_start_ids": set(),
            "orphan_end_ids": set(),
            "orphan_start_samples": [],
            "orphan_end_samples": [],
        }
        for name in RANGE_TAGS
    }


def _collect_range_stats(part_name: str, root, aggregate: dict[str, dict[str, object]]) -> None:
    for range_name, (start_tag, end_tag) in RANGE_TAGS.items():
        starts = Counter(
            elem.get(_w("id"))
            for elem in root.findall(f".//{_w(start_tag)}")
            if elem.get(_w("id")) is not None
        )
        ends = Counter(
            elem.get(_w("id"))
            for elem in root.findall(f".//{_w(end_tag)}")
            if elem.get(_w("id")) is not None
        )

        item = aggregate[range_name]
        item["start_count"] += sum(starts.values())
        item["end_count"] += sum(ends.values())

        for range_id in sorted(set(starts) | set(ends)):
            start_count = starts.get(range_id, 0)
            end_count = ends.get(range_id, 0)
            if start_count > end_count:
                item["orphan_start_ids"].add(range_id)
                if len(item["orphan_start_samples"]) < 10:
                    item["orphan_start_samples"].append(
                        {
                            "id": range_id,
                            "part": part_name,
                            "start_count": start_count,
                            "end_count": end_count,
                        }
                    )
            if end_count > start_count:
                item["orphan_end_ids"].add(range_id)
                if len(item["orphan_end_samples"]) < 10:
                    item["orphan_end_samples"].append(
                        {
                            "id": range_id,
                            "part": part_name,
                            "start_count": start_count,
                            "end_count": end_count,
                        }
                    )


def _finalize_ranges(aggregate: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for name, item in aggregate.items():
        out[name] = {
            "start_count": item["start_count"],
            "end_count": item["end_count"],
            "orphan_start_ids": sorted(item["orphan_start_ids"]),
            "orphan_end_ids": sorted(item["orphan_end_ids"]),
            "orphan_start_samples": item["orphan_start_samples"],
            "orphan_end_samples": item["orphan_end_samples"],
        }
    return out


def _document_relationship_issues(
    zf: zipfile.ZipFile,
    names: set[str],
) -> tuple[list[dict[str, object]], list[str]]:
    rel_path = "word/_rels/document.xml.rels"
    if rel_path not in names:
        return [], []

    root = _read_xml(zf, rel_path)
    missing_targets: list[dict[str, object]] = []
    rel_ids: list[str] = []
    for rel in root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        rel_id = rel.get("Id") or ""
        target = rel.get("Target")
        mode = rel.get("TargetMode")
        rel_ids.append(rel_id)
        if mode == "External":
            continue
        if not target:
            missing_targets.append({"id": rel_id, "target": target, "reason": "empty_target"})
            continue
        resolved = _resolve_rel_target(rel_path, target)
        if resolved not in names:
            missing_targets.append(
                {
                    "id": rel_id,
                    "target": target,
                    "resolved_target": resolved,
                    "reason": "missing_target",
                }
            )
    return missing_targets, sorted(rel_ids)


def _dangling_document_rids(
    zf: zipfile.ZipFile,
    names: set[str],
    rel_ids: list[str],
) -> list[str]:
    if "word/document.xml" not in names:
        return []
    doc_root = _read_xml(zf, "word/document.xml")
    rel_id_set = set(rel_ids)
    dangling: set[str] = set()
    for elem in doc_root.iter():
        for attr_name, attr_value in elem.attrib.items():
            qname = etree.QName(attr_name)
            if qname.namespace == R_NS and qname.localname == "id" and attr_value not in rel_id_set:
                dangling.add(attr_value)
    return sorted(dangling)


def analyze_docx(path: str | Path) -> dict[str, object]:
    path = Path(path)
    report: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "zip_ok": False,
        "required_parts_missing": [],
        "xml_parse_errors": [],
        "document_relationship_missing_targets": [],
        "dangling_rids_in_document": [],
        "document_body": {
            "last_child": None,
            "sectpr_is_last": False,
            "direct_sectpr_count": 0,
        },
        "ranges": _finalize_ranges(_empty_range_aggregate()),
    }

    if not path.exists():
        report["error"] = "file_not_found"
        return report

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            report["zip_ok"] = True
            report["required_parts_missing"] = [
                name for name in ("[Content_Types].xml", "word/document.xml") if name not in names
            ]

            ranges = _empty_range_aggregate()
            for xml_name in _word_xml_parts(names):
                try:
                    root = _read_xml(zf, xml_name)
                except etree.XMLSyntaxError as exc:
                    report["xml_parse_errors"].append({"part": xml_name, "error": str(exc)})
                    continue
                except Exception as exc:  # pragma: no cover
                    report["xml_parse_errors"].append({"part": xml_name, "error": repr(exc)})
                    continue

                if xml_name == "word/document.xml":
                    report["document_body"] = _body_summary(root)
                if xml_name in _story_parts(names):
                    _collect_range_stats(xml_name, root, ranges)

            report["ranges"] = _finalize_ranges(ranges)
            rel_issues, rel_ids = _document_relationship_issues(zf, names)
            report["document_relationship_missing_targets"] = rel_issues
            report["dangling_rids_in_document"] = _dangling_document_rids(zf, names, rel_ids)
    except zipfile.BadZipFile:
        report["error"] = "bad_zip_file"
    except Exception as exc:  # pragma: no cover
        report["error"] = repr(exc)

    return report


def summarize_semantic_issues(report: dict[str, object]) -> list[str]:
    issues: list[str] = []
    if not report.get("exists"):
        return ["file_not_found"]
    if not report.get("zip_ok"):
        return [str(report.get("error") or "zip_error")]
    if report.get("required_parts_missing"):
        issues.append(f"missing_parts={report['required_parts_missing']}")
    if report.get("xml_parse_errors"):
        issues.append(f"xml_parse_errors={len(report['xml_parse_errors'])}")
    if report.get("document_relationship_missing_targets"):
        issues.append(
            f"broken_document_relationships={len(report['document_relationship_missing_targets'])}"
        )
    if report.get("dangling_rids_in_document"):
        issues.append(f"dangling_rids={report['dangling_rids_in_document']}")
    body = report.get("document_body", {})
    if body and not body.get("sectpr_is_last", False):
        issues.append(f"body_last_child={body.get('last_child')}")

    for range_name, stats in (report.get("ranges") or {}).items():
        orphan_start_ids = stats.get("orphan_start_ids") or []
        orphan_end_ids = stats.get("orphan_end_ids") or []
        if orphan_start_ids or orphan_end_ids:
            issues.append(
                f"{range_name}:orphan_start={orphan_start_ids},orphan_end={orphan_end_ids}"
            )
    return issues
