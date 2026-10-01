import argparse
import copy
import glob
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List


def _collect_json_files(input_path: str) -> List[str]:
    if os.path.isdir(input_path):
        return sorted(glob.glob(os.path.join(input_path, "**", "*.json"), recursive=True))
    if os.path.isfile(input_path) and input_path.lower().endswith(".json"):
        return [input_path]
    return sorted(glob.glob(input_path, recursive=True))


def _read_json_list(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: top-level JSON must be a list.")
    return data


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _relative_to_base(path: str, base: str) -> str:
    if os.path.isdir(base):
        return os.path.relpath(path, base)
    return os.path.basename(path)


def _write_lines(path: str, lines: List[str]):
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n").replace("\r", "\n")
    if raw.endswith("\n"):
        raw = raw[:-1]
    if raw == "":
        return [""]
    return raw.split("\n")


def _extract_tags(text: str) -> List[str]:
    return re.findall(r"<[^>]+>", text or "")


def _normalize_tag_content(content: str) -> str:
    c = content.strip().lower()
    c = c.replace("_", "").replace("-", "").replace(" ", "")
    # Korean/English mixed variants
    if any(k in c for k in ("vocalsound", "vocal")) or ("보컬" in content) or ("사운드" in content):
        return "vocalsound"
    if any(k in c for k in ("disfmarker", "disfluency", "filler")) or ("머뭇" in content):
        return "disfmarker"
    if (
        "gap" in c
        or "pause" in c
        or ("공백" in content)
        or ("침묵" in content)
        or ("잠시" in content and "멈춤" in content)
    ):
        return "gap"
    return c


def _repair_tags(source_text: str, translated_text: str) -> str:
    src_tags = _extract_tags(source_text)
    if not src_tags:
        return translated_text
    out = translated_text or ""
    tr_tags = _extract_tags(out)
    if tr_tags:
        # 1) positional replace first
        for i, tr in enumerate(tr_tags):
            if i < len(src_tags):
                out = out.replace(tr, src_tags[i], 1)
            else:
                out = out.replace(tr, "", 1)
    else:
        # 2) if translator removed brackets but translated tag words remain, recover by source order
        # Keep simple: if source has tags and none in target, prepend missing tags.
        out = " ".join(src_tags) + (" " + out if out else "")
    # 3) clean accidental translated tags that still remain in brackets
    rem = _extract_tags(out)
    for t in rem:
        inner = t[1:-1]
        norm = _normalize_tag_content(inner)
        if norm in ("vocalsound", "disfmarker", "gap"):
            # try to align to source by type order if available
            candidates = [s for s in src_tags if norm in s.lower()]
            if candidates:
                out = out.replace(t, candidates[0], 1)
    return re.sub(r"\s{2,}", " ", out).strip()


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _xlsx_col(n: int) -> str:
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _make_sheet_xml(lines: List[str]) -> str:
    rows = []
    rows.append(
        '<row r="1">'
        '<c r="A1" t="inlineStr"><is><t xml:space="preserve">idx</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t xml:space="preserve">source</t></is></c>'
        '<c r="C1" t="inlineStr"><is><t xml:space="preserve">translation</t></is></c>'
        "</row>"
    )
    for i, text in enumerate(lines, start=2):
        a = f'<c r="A{i}"><v>{i-1}</v></c>'
        b = (
            f'<c r="B{i}" t="inlineStr"><is><t xml:space="preserve">{_xml_escape(text)}</t></is></c>'
        )
        c = f'<c r="C{i}" t="inlineStr"><is><t xml:space="preserve"></t></is></c>'
        rows.append(f'<row r="{i}">{a}{b}{c}</row>')
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(rows)
        + "</sheetData></worksheet>"
    )
    return xml


def _write_xlsx(path: str, lines: List[str]):
    _ensure_dir(os.path.dirname(path))
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf/></cellStyleXfs>
  <cellXfs count="1"><xf xfId="0"/></cellXfs>
</styleSheet>"""
    sheet1 = _make_sheet_xml(lines)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", styles)
        zf.writestr("xl/worksheets/sheet1.xml", sheet1)


def _cell_col_ref(cell_ref: str) -> str:
    out = []
    for ch in cell_ref:
        if ch.isalpha():
            out.append(ch)
        else:
            break
    return "".join(out).upper()


def _read_shared_strings(zf: zipfile.ZipFile):
    name = "xl/sharedStrings.xml"
    if name not in zf.namelist():
        return []
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(zf.read(name))
    values = []
    for si in root.findall("s:si", ns):
        parts = [t.text or "" for t in si.findall(".//s:t", ns)]
        values.append("".join(parts))
    return values


def _resolve_first_sheet_path(zf: zipfile.ZipFile) -> str:
    ns_main = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    ns_rel = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    first_sheet = wb.find("s:sheets/s:sheet", ns_main)
    if first_sheet is None:
        raise ValueError("xlsx has no sheet")
    rid = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if not rid:
        raise ValueError("sheet relationship id missing")
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel in rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
        if rel.attrib.get("Id") == rid:
            target = rel.attrib.get("Target", "")
            return "xl/" + target if not target.startswith("xl/") else target
    raise ValueError("sheet target not found")


def _xlsx_read_lines(path: str, translated_col: str = "C", source_col: str = "B") -> List[str]:
    translated_col = translated_col.upper()
    source_col = source_col.upper()
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path, "r") as zf:
        shared = _read_shared_strings(zf)
        sheet_path = _resolve_first_sheet_path(zf)
        root = ET.fromstring(zf.read(sheet_path))
    lines = []
    for row in root.findall(".//s:sheetData/s:row", ns):
        r = int(row.attrib.get("r", "0"))
        if r <= 1:
            continue
        values = {}
        for c in row.findall("s:c", ns):
            ref = c.attrib.get("r", "")
            col = _cell_col_ref(ref)
            ctype = c.attrib.get("t", "")
            text = ""
            if ctype == "inlineStr":
                parts = [t.text or "" for t in c.findall(".//s:t", ns)]
                text = "".join(parts)
            elif ctype == "s":
                v = c.find("s:v", ns)
                if v is not None and v.text and v.text.isdigit():
                    idx = int(v.text)
                    if 0 <= idx < len(shared):
                        text = shared[idx]
            else:
                v = c.find("s:v", ns)
                text = (v.text or "") if v is not None else ""
            values[col] = text
        translated = values.get(translated_col, "")
        if translated == "":
            translated = values.get(source_col, "")
        lines.append(translated)
    return lines


def export_mode(args):
    files = _collect_json_files(args.input)
    if not files:
        raise RuntimeError("No JSON files matched input.")
    count = 0
    for src in files:
        items = _read_json_list(src)
        lines = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"{src}: list item {i} is not an object.")
            value = item.get(args.field, "")
            if value is None:
                value = ""
            if not isinstance(value, str):
                value = str(value)
            value = value.replace("\r\n", " ").replace("\n", " ")
            lines.append(value)
        rel = _relative_to_base(src, args.input)
        out_rel = os.path.splitext(rel)[0] + ".txt"
        out_path = os.path.join(args.output, out_rel)
        _write_lines(out_path, lines)
        print(f"export: {src} -> {out_path} ({len(lines)} lines)")
        count += 1
    print(f"done export: {count} file(s)")


def export_xlsx_mode(args):
    files = _collect_json_files(args.input)
    if not files:
        raise RuntimeError("No JSON files matched input.")
    count = 0
    for src in files:
        items = _read_json_list(src)
        lines = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"{src}: list item {i} is not an object.")
            value = item.get(args.field, "")
            if value is None:
                value = ""
            if not isinstance(value, str):
                value = str(value)
            value = value.replace("\r\n", " ").replace("\n", " ")
            lines.append(value)
        rel = _relative_to_base(src, args.input)
        out_rel = os.path.splitext(rel)[0] + ".xlsx"
        out_path = os.path.join(args.output, out_rel)
        _write_xlsx(out_path, lines)
        print(f"export-xlsx: {src} -> {out_path} ({len(lines)} rows)")
        count += 1
    print(f"done export-xlsx: {count} file(s)")


def import_mode(args):
    files = _collect_json_files(args.input)
    if not files:
        raise RuntimeError("No JSON files matched input.")
    count = 0
    for src in files:
        items = _read_json_list(src)
        rel = _relative_to_base(src, args.input)
        txt_rel = os.path.splitext(rel)[0] + ".txt"
        txt_path = os.path.join(args.translated, txt_rel)
        if not os.path.exists(txt_path):
            if args.skip_missing:
                print(f"skip: missing translated file {txt_path}")
                continue
            raise FileNotFoundError(f"Missing translated text file: {txt_path}")
        lines = _read_lines(txt_path)
        if len(lines) != len(items):
            raise ValueError(
                f"Line count mismatch for {txt_path}: got {len(lines)} expected {len(items)}"
            )
        out_items = copy.deepcopy(items)
        for i, text in enumerate(lines):
            if not isinstance(out_items[i], dict):
                raise ValueError(f"{src}: list item {i} is not an object.")
            src_text = out_items[i].get(args.field, "")
            out_items[i][args.field] = _repair_tags(src_text, text)
        out_path = os.path.join(args.output, rel)
        _ensure_dir(os.path.dirname(out_path))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_items, f, ensure_ascii=False)
        print(f"import: {txt_path} -> {out_path} ({len(lines)} lines)")
        count += 1
    print(f"done import: {count} file(s)")


def import_xlsx_mode(args):
    files = _collect_json_files(args.input)
    if not files:
        raise RuntimeError("No JSON files matched input.")
    count = 0
    for src in files:
        items = _read_json_list(src)
        rel = _relative_to_base(src, args.input)
        xlsx_rel = os.path.splitext(rel)[0] + ".xlsx"
        xlsx_path = os.path.join(args.translated, xlsx_rel)
        if not os.path.exists(xlsx_path):
            if args.skip_missing:
                print(f"skip: missing translated file {xlsx_path}")
                continue
            raise FileNotFoundError(f"Missing translated xlsx file: {xlsx_path}")
        lines = _xlsx_read_lines(
            xlsx_path,
            translated_col=args.translated_col,
            source_col=args.source_col,
        )
        if len(lines) != len(items):
            raise ValueError(
                f"Row count mismatch for {xlsx_path}: got {len(lines)} expected {len(items)}"
            )
        out_items = copy.deepcopy(items)
        for i, text in enumerate(lines):
            if not isinstance(out_items[i], dict):
                raise ValueError(f"{src}: list item {i} is not an object.")
            src_text = out_items[i].get(args.field, "")
            out_items[i][args.field] = _repair_tags(src_text, text)
        out_path = os.path.join(args.output, rel)
        _ensure_dir(os.path.dirname(out_path))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_items, f, ensure_ascii=False)
        print(f"import-xlsx: {xlsx_path} -> {out_path} ({len(lines)} rows)")
        count += 1
    print(f"done import-xlsx: {count} file(s)")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Convert JSON list field values to line-based TXT and back."
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    p_export = sub.add_parser("export", help="Export JSON field values to TXT lines")
    p_export.add_argument("--input", required=True, help="Input JSON file/dir/glob")
    p_export.add_argument("--output", required=True, help="Output directory for TXT files")
    p_export.add_argument(
        "--field",
        default="text",
        help="JSON field name to export (default: text)",
    )
    p_export.set_defaults(func=export_mode)

    p_export_xlsx = sub.add_parser(
        "export-xlsx", help="Export JSON field values to XLSX rows (Google Translate-friendly)"
    )
    p_export_xlsx.add_argument("--input", required=True, help="Input JSON file/dir/glob")
    p_export_xlsx.add_argument(
        "--output",
        required=True,
        help="Output directory for XLSX files",
    )
    p_export_xlsx.add_argument(
        "--field",
        default="text",
        help="JSON field name to export (default: text)",
    )
    p_export_xlsx.set_defaults(func=export_xlsx_mode)

    p_import = sub.add_parser("import", help="Import translated TXT lines back into JSON")
    p_import.add_argument("--input", required=True, help="Source JSON file/dir/glob (template)")
    p_import.add_argument(
        "--translated",
        required=True,
        help="Directory containing translated TXT files",
    )
    p_import.add_argument("--output", required=True, help="Output directory for translated JSON")
    p_import.add_argument(
        "--field",
        default="text",
        help="JSON field name to replace (default: text)",
    )
    p_import.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip JSON files that do not have matching translated TXT files",
    )
    p_import.set_defaults(func=import_mode)

    p_import_xlsx = sub.add_parser(
        "import-xlsx", help="Import translated XLSX rows back into JSON"
    )
    p_import_xlsx.add_argument(
        "--input", required=True, help="Source JSON file/dir/glob (template)"
    )
    p_import_xlsx.add_argument(
        "--translated",
        required=True,
        help="Directory containing translated XLSX files",
    )
    p_import_xlsx.add_argument(
        "--output", required=True, help="Output directory for translated JSON"
    )
    p_import_xlsx.add_argument(
        "--field",
        default="text",
        help="JSON field name to replace (default: text)",
    )
    p_import_xlsx.add_argument(
        "--translated-col",
        default="C",
        help="XLSX column letter that has translated text (default: C)",
    )
    p_import_xlsx.add_argument(
        "--source-col",
        default="B",
        help="Fallback column letter if translated cell is empty (default: B)",
    )
    p_import_xlsx.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip JSON files that do not have matching translated XLSX files",
    )
    p_import_xlsx.set_defaults(func=import_xlsx_mode)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
