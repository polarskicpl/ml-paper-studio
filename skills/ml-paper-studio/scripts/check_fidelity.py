#!/usr/bin/env python3
"""List mechanical translation-drift candidates; this is not semantic validation."""
import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys


NUMBER = re.compile(
    r"(?<![A-Za-z0-9_.])[-+]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?:\\?%)?(?![A-Za-z0-9_.])"
)
CITATION = re.compile(r"\\cite(?:p|t)?\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^{}]*)\}")
DISPLAY = re.compile(
    r"(?<!\\)\$\$(.*?)(?<!\\)\$\$|\\\[(.*?)\\\]|"
    r"\\begin\{((?:equation|align)\*?)\}(.*?)\\end\{\3\}", re.S
)
LIMITATIONS = [
    "Only mechanical candidates are reported; neither status proves paper quality, correctness, or submission readiness.",
    "Numbers form an unordered multiset: swapped locations can be missed; section/page numbers, dates, labels, code, and comments can cause false alarms.",
    "Chinese quantity units (万/亿), English million/billion, unit conversions, rounding, percentage/fraction equivalence, and uncertainty notation are not interpreted.",
    "Grouping commas and e/E scientific notation are normalized; decimal commas, spaced digit groups, and TeX times-10 notation are not parsed as equivalent numbers.",
    "Only literal cite/citep/citet LaTeX keys are compared as a set; citation placement, support, metadata, macros, and Markdown references need review.",
    "Only dollar-dollar, bracket display math, and equation/align environments are inspected; inline math and other environments are outside scope.",
    "Formula hashes ignore all whitespace and display delimiters; whitespace-sensitive text can be missed, while labels or equivalent algebra can produce candidates.",
    "No statistical validity, mathematical equivalence, causal meaning, translation meaning, or source authenticity is established by this script.",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_number(token):
    percent = token.endswith("%")
    token = token.rstrip("%").rstrip("\\").replace(",", "")
    value = Decimal(token)
    parts = value.as_tuple()
    digits = "".join(map(str, parts.digits)).lstrip("0") or "0"
    exponent = parts.exponent
    while digits != "0" and digits.endswith("0"):
        digits, exponent = digits[:-1], exponent + 1
    if digits == "0":
        number = "0"
    else:
        number = ("-" if parts.sign else "") + digits
        if exponent:
            number += "e" + str(exponent)
    return number + ("%" if percent else "")


def inspect(text):
    normalized = text.replace("−", "-").replace("－", "-").replace("％", "%")
    numbers = Counter(canonical_number(m.group()) for m in NUMBER.finditer(normalized))
    keys = {key.strip() for match in CITATION.finditer(text)
            for key in match.group(1).split(",") if key.strip()}
    formulas, examples = Counter(), {}
    for match in DISPLAY.finditer(text):
        body = next(value for value in (match.group(1), match.group(2), match.group(4))
                    if value is not None)
        compact = re.sub(r"\s+", "", body)
        digest = sha256(compact.encode("utf-8"))
        formulas[digest] += 1
        examples.setdefault(digest, body.strip()[:180])
    return numbers, keys, formulas, examples


def counts(counter, field="value", examples=None):
    rows = []
    for value, count in sorted(counter.items()):
        row = {field: value, "count": count}
        if examples is not None:
            row["example"] = examples[value]
        rows.append(row)
    return rows


def build_report(source, target, source_bytes, target_bytes):
    src = inspect(source_bytes.decode("utf-8"))
    dst = inspect(target_bytes.decode("utf-8"))
    numeric = {"missing_from_target": counts(src[0] - dst[0]),
               "added_in_target": counts(dst[0] - src[0])}
    citation = {"missing_from_target": sorted(src[1] - dst[1]),
                "added_in_target": sorted(dst[1] - src[1])}
    formula = {"source_count": sum(src[2].values()), "target_count": sum(dst[2].values()),
               "missing_from_target": counts(src[2] - dst[2], "sha256", src[3]),
               "added_in_target": counts(dst[2] - src[2], "sha256", dst[3])}
    changed = any(group[key] for group in (numeric, citation, formula)
                  for key in ("missing_from_target", "added_in_target"))
    return {
        "schema_version": 1,
        "status": "needs_semantic_review" if changed else "no_mechanical_delta",
        "source": {"path": str(source), "sha256": sha256(source_bytes)},
        "target": {"path": str(target), "sha256": sha256(target_bytes)},
        "numeric": numeric, "citation": citation, "formula": formula,
        "limitations": LIMITATIONS,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="UTF-8 Chinese source")
    parser.add_argument("--target", type=Path, required=True, help="UTF-8 English target")
    parser.add_argument("--output", type=Path, help="Optional JSON report file")
    args = parser.parse_args(argv)
    try:
        source_bytes, target_bytes = args.source.read_bytes(), args.target.read_bytes()
        if args.output is not None:
            for original in (args.source, args.target):
                if args.output.resolve() == original.resolve() or (
                    args.output.exists() and args.output.samefile(original)
                ):
                    raise ValueError("Report output must not overwrite either input")
        report = build_report(args.source, args.target, source_bytes, target_bytes)
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output is not None:
            args.output.write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return int(report["status"] == "needs_semantic_review")
    except (OSError, UnicodeError, ValueError, InvalidOperation) as error:
        sys.stderr.write(json.dumps({"status": "error", "error": str(error)},
                                    ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
