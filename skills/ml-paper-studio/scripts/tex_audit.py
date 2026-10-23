#!/usr/bin/env python3
"""Audit literal TeX links locally. This program never runs TeX or uses a network."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


COMMAND = re.compile(r"\\([A-Za-z@]+|[^\n])")
VERBATIM = {"verbatim", "verbatim*", "Verbatim", "lstlisting", "minted", "comment"}
DEFINITIONS = {"newcommand", "renewcommand", "providecommand", "DeclareRobustCommand",
               "NewDocumentCommand", "RenewDocumentCommand", "ProvideDocumentCommand",
               "newenvironment", "renewenvironment", "def", "gdef", "edef", "xdef"}
REFS = {"ref", "eqref", "autoref", "cref", "Cref", "pageref", "nameref", "vref", "Vref"}
CITES = {"cite", "citep", "citet", "Citep", "Citet", "citealt", "citealp", "nocite",
         "parencite", "textcite", "autocite", "footcite"}
GRAPHICS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".webp", ".tif", ".tiff", ".pgf")
TRACKED = re.compile(r"\\(?:input|include|label|ref|eqref|autoref|cref|cite\w*|bibliography|addbibresource|bibitem)\b")


def escaped(text: str, pos: int) -> bool:
    count = 0
    pos -= 1
    while pos >= 0 and text[pos] == "\\":
        count += 1
        pos -= 1
    return bool(count % 2)


def skip_space(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def group(text: str, pos: int, opening: str = "{", closing: str = "}"):
    """Read a balanced literal group without interpreting its TeX contents."""
    pos = skip_space(text, pos)
    if pos >= len(text) or text[pos] != opening:
        return None
    start, depth = pos + 1, 1
    pos += 1
    while pos < len(text):
        if not escaped(text, pos):
            if text[pos] == opening:
                depth += 1
            elif text[pos] == closing:
                depth -= 1
                if not depth:
                    return text[start:pos], pos + 1
        pos += 1
    return None


def argument(text: str, pos: int):
    pos = skip_space(text, pos)
    if pos < len(text) and text[pos] == "*":
        pos = skip_space(text, pos + 1)
    while pos < len(text) and text[pos] == "[":
        opt = group(text, pos, "[", "]")
        if opt is None:
            return None
        pos = skip_space(text, opt[1])
    return group(text, pos)


def definition_end(text: str, pos: int, name: str):
    pos = skip_space(text, pos)
    if pos < len(text) and text[pos] == "*":
        pos = skip_space(text, pos + 1)
    if name in {"def", "gdef", "edef", "xdef"}:
        found = text.find("{", pos)
        if found < 0:
            return None
        body = group(text, found)
        return body[1] if body else None
    target = group(text, pos)
    if target:
        pos = target[1]
    else:
        token = COMMAND.match(text, pos)
        if not token:
            return None
        pos = token.end()
    pos = skip_space(text, pos)
    while pos < len(text) and text[pos] == "[":
        opt = group(text, pos, "[", "]")
        if not opt:
            return None
        pos = skip_space(text, opt[1])
    count = 2 if name.endswith("DocumentCommand") or name.endswith("environment") else 1
    for _ in range(count):
        body = group(text, pos)
        if not body:
            return None
        pos = body[1]
    return pos


class Audit:
    def __init__(self, root: Path):
        self.root = root
        self.findings = []
        self.files = {}
        self.tex_paths = set()
        self.labels = {}
        self.references = []
        self.citations = []
        self.bib_requests = []
        self.graphics_requests = []
        self.graphics_dirs = [root]
        self.bib_keys = set()
        self.dynamic_labels = False
        self.dynamic_bib = False
        self.counts = {"tex_files": 0, "bibliography_files": 0, "graphics_files": 0,
                       "labels": 0, "references": 0, "citation_keys": 0}

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def finding(self, severity, code, path, line, message):
        self.findings.append({"severity": severity, "code": code,
                              "file": self.rel(path) if path else None,
                              "line": line, "message": message})

    def safe(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("path resolves outside --root (including symlink targets)") from exc
        return resolved

    def record(self, path: Path):
        if path in self.files:
            return
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        self.files[path] = {"path": self.rel(path), "sha256": digest.hexdigest()}

    def literal(self, raw, path, line, kind):
        value = raw.strip()
        # These control symbols encode literal filename characters, not macros.
        dynamic_probe = re.sub(r"\\([%_&#${}])", "", value)
        if not value or any(char in dynamic_probe for char in "\\#${}\x00\n\r"):
            self.finding("warning", "dynamic_" + kind, path, line,
                         "Cannot resolve this nonliteral or empty argument statically: " + raw)
            return None
        return re.sub(r"\\([%_&#${}])", lambda match: match.group(1), value)

    def preprocess(self, text, path):
        chars = list(text)

        def mask(start, end):
            for offset in range(start, end):
                if chars[offset] != "\n":
                    chars[offset] = " "

        pos = 0
        while pos < len(text):
            if text[pos] == "%" and not escaped(text, pos):
                end = text.find("\n", pos)
                end = len(text) if end < 0 else end
                mask(pos, end)
                pos = end
                continue
            token = COMMAND.match(text, pos) if text[pos] == "\\" else None
            if not token:
                pos += 1
                continue
            name = token.group(1)
            line = text.count("\n", 0, pos) + 1
            if name == "verb":
                start = token.end()
                if start < len(text) and text[start] == "*":
                    start += 1
                if start < len(text) and not text[start].isspace():
                    end = text.find(text[start], start + 1)
                    newline = text.find("\n", start)
                    if end >= 0 and (newline < 0 or end < newline):
                        mask(pos, end + 1)
                        pos = end + 1
                        continue
                end = text.find("\n", pos)
                end = len(text) if end < 0 else end
                self.finding("warning", "unparsed_verb", path, line,
                             "Inline verbatim could not be bounded; line remainder not checked.")
                mask(pos, end)
                pos = end
                continue
            if name == "begin":
                env = group(text, token.end())
                if env and env[0] in VERBATIM:
                    closing = "\\end{" + env[0] + "}"
                    end = text.find(closing, env[1])
                    if end < 0:
                        self.finding("warning", "unclosed_verbatim", path, line,
                                     "Verbatim environment could not be bounded; remainder not checked.")
                        self.dynamic_labels = True
                        self.dynamic_bib = True
                        end = len(text)
                    else:
                        end += len(closing)
                    mask(pos, end)
                    pos = end
                    continue
            pos = token.end()
        # Strip comments before balancing definitions: braces inside a comment do
        # not terminate a macro body. Keep original offsets and line numbers.
        clean = "".join(chars)
        pos = 0
        while True:
            token = COMMAND.search(clean, pos)
            if token is None:
                break
            pos = token.end()
            name = token.group(1)
            if name in DEFINITIONS:
                end = definition_end(clean, token.end(), name)
                if end:
                    if TRACKED.search(clean[token.end():end]):
                        self.dynamic_labels = True
                        self.dynamic_bib = True
                        self.finding("warning", "macro_not_expanded", path,
                                     clean.count("\n", 0, token.start()) + 1,
                                     "A macro definition contains audited commands; its execution is not modeled.")
                    mask(token.start(), end)
                    pos = end
                    continue
        return "".join(chars)

    def locate(self, raw, path, line, kind, extensions=(), dirs=None):
        value = self.literal(raw, path, line, kind)
        if value is None:
            return None
        base = Path(value)
        candidates = []
        for directory in dirs or [self.root]:
            candidate = base if base.is_absolute() else directory / base
            candidates.append(candidate)
            if not base.suffix:
                candidates.extend(Path(str(candidate) + ext) for ext in extensions)
        try:
            safe_candidates = [self.safe(candidate) for candidate in candidates]
        except (ValueError, OSError, RuntimeError) as exc:
            self.finding("error", "path_outside_root", path, line, str(exc) + ": " + value)
            return None
        for candidate in safe_candidates:
            if candidate.is_file():
                return candidate
        self.finding("error", "missing_" + kind, path, line,
                     "No local file found for literal argument: " + value)
        return None

    def scan(self, path, stack=()):
        if path in stack:
            self.finding("error", "include_cycle", path, 1, "Literal include/input cycle detected.")
            return
        try:
            self.record(path)
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            self.finding("error", "unreadable_tex", path, 1, str(exc))
            return
        self.tex_paths.add(path)
        self.counts["tex_files"] = len(self.tex_paths)
        clean = self.preprocess(text, path)
        pos = 0
        while True:
            token = COMMAND.search(clean, pos)
            if not token:
                break
            name, pos = token.group(1), token.end()
            known = name in REFS or name in CITES or name in {
                "input", "include", "label", "bibliography", "addbibresource",
                "includegraphics", "graphicspath", "bibitem"}
            if not known:
                if name in {"import", "subimport", "subfile", "includeonly"}:
                    self.dynamic_labels = True
                    self.dynamic_bib = True
                    self.finding("warning", "unsupported_file_macro", path,
                                 clean.count("\n", 0, token.start()) + 1,
                                 "File-selection macro is not modeled: \\" + name)
                continue
            line = clean.count("\n", 0, token.start()) + 1
            arg = argument(clean, pos)
            if arg is None:
                # TeX permits unbraced input; do not mistake it for a confirmed missing file.
                if name in {"input", "include"}:
                    self.dynamic_labels = True
                    self.dynamic_bib = True
                self.finding("warning", "unparsed_argument", path, line,
                             "Expected a literal braced argument for \\" + name)
                continue
            raw, pos = arg
            if name in {"input", "include"}:
                target = self.locate(raw, path, line, "include", (".tex",))
                if target:
                    self.scan(target, stack + (path,))
                elif self.findings and self.findings[-1]["code"] == "dynamic_include":
                    self.dynamic_labels = True
                    self.dynamic_bib = True
            elif name == "label":
                key = self.literal(raw, path, line, "label")
                if key is None:
                    self.dynamic_labels = True
                elif key in self.labels:
                    earlier = self.labels[key]
                    self.finding("error", "duplicate_label", path, line,
                                 f"Duplicate label {key!r}; first at {earlier[0]}:{earlier[1]}.")
                else:
                    self.labels[key] = (self.rel(path), line)
                    self.counts["labels"] += 1
            elif name in REFS:
                for raw_key in raw.split(",") if name in {"cref", "Cref"} else [raw]:
                    key = self.literal(raw_key, path, line, "reference")
                    if key is not None:
                        self.references.append((key, path, line))
            elif name in CITES:
                for raw_key in raw.split(","):
                    if name == "nocite" and raw_key.strip() == "*":
                        continue
                    key = self.literal(raw_key, path, line, "citation")
                    if key is not None:
                        self.citations.append((key, path, line))
            elif name in {"bibliography", "addbibresource"}:
                for item in raw.split(",") if name == "bibliography" else [raw]:
                    if "\\" in item:
                        self.dynamic_bib = True
                    self.bib_requests.append((item, path, line))
            elif name == "bibitem":
                key = self.literal(raw, path, line, "bibitem")
                if key is None:
                    self.dynamic_bib = True
                else:
                    self.bib_keys.add(key)
            elif name == "includegraphics":
                self.graphics_requests.append((raw, path, line))
            elif name == "graphicspath":
                offset = 0
                while skip_space(raw, offset) < len(raw):
                    directory = group(raw, offset)
                    if directory is None:
                        self.finding("warning", "unparsed_graphicspath", path, line,
                                     "Could not parse every graphics directory.")
                        break
                    value = self.literal(directory[0], path, line, "graphics_directory")
                    if value is not None:
                        try:
                            self.graphics_dirs.append(self.safe(self.root / value))
                        except (ValueError, OSError, RuntimeError) as exc:
                            self.finding("error", "path_outside_root", path, line, str(exc))
                    offset = directory[1]

    def finish(self):
        seen_bib = set()
        for raw, source, line in self.bib_requests:
            path = self.locate(raw, source, line, "bibliography", (".bib",))
            if path is None or path in seen_bib:
                continue
            seen_bib.add(path)
            try:
                self.record(path)
                content = path.read_text(encoding="utf-8-sig")
                content = re.sub(r"(?m)^\s*%[^\n]*", "", content)
            except (OSError, UnicodeError) as exc:
                self.finding("error", "unreadable_bibliography", source, line, str(exc))
                continue
            self.counts["bibliography_files"] += 1
            # Consume whole entries so an @ sign inside a field cannot invent a key.
            offset = 0
            entry = re.compile(r"@([A-Za-z]+)\s*([({])")
            while True:
                match = entry.search(content, offset)
                if match is None:
                    break
                opener = match.group(2)
                body = group(content, match.end() - 1, opener, "}" if opener == "{" else ")")
                if body is None:
                    self.finding("warning", "unparsed_bib_entry", path,
                                 content.count("\n", 0, match.start()) + 1,
                                 "Bibliography entry could not be bounded; key checks may be incomplete.")
                    self.dynamic_bib = True
                    break
                offset = body[1]
                if match.group(1).lower() not in {"comment", "string", "preamble"}:
                    key = body[0].split(",", 1)[0].strip()
                    if key:
                        self.bib_keys.add(key)
        seen_graphics = set()
        for raw, source, line in self.graphics_requests:
            path = self.locate(raw, source, line, "graphics", GRAPHICS, self.graphics_dirs)
            if path and path not in seen_graphics:
                try:
                    self.record(path)
                    seen_graphics.add(path)
                except OSError as exc:
                    self.finding("error", "unreadable_graphics", source, line, str(exc))
        self.counts["graphics_files"] = len(seen_graphics)
        self.counts["references"] = len(self.references)
        self.counts["citation_keys"] = len(self.citations)
        for key, source, line in self.references:
            if key not in self.labels:
                self.finding("warning" if self.dynamic_labels else "error", "missing_label", source, line,
                             "No literal label found for " + repr(key) +
                             ("; macro-generated labels remain possible." if self.dynamic_labels else "."))
        for key, source, line in self.citations:
            if key not in self.bib_keys:
                self.finding("warning" if self.dynamic_bib else "error", "missing_citation_key", source, line,
                             "No bibliography entry found for " + repr(key) +
                             ("; dynamically loaded entries remain possible." if self.dynamic_bib else "."))

    def report(self):
        return {
            "schema": "ml-paper-studio.tex-audit/1",
            "status": "needs_review" if self.findings else "clean_static",
            "checks": self.counts,
            "findings": self.findings,
            "scanned_files": sorted(self.files.values(), key=lambda item: item["path"]),
            "limitations": [
                "Static lexical checks only; no TeX engine, shell command, or network call is executed.",
                "Passing does not prove mathematical correctness, bibliographic authenticity, visual quality, or venue compliance.",
                "Custom/dynamic macros, conditionals, package behavior, catcodes, and generated resources are not fully modeled.",
                "Literal file paths are resolved from --root, assumed to be the TeX working directory; graphicspath scopes are not modeled.",
                "Bibliography keys are checked locally; this is not a complete BibTeX/Biber syntax validator or citation-support audit.",
            ],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--main", default="main.tex")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    audit = None
    exit_code = 2
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("--root must be an existing directory")
        audit = Audit(root)
        primary = audit.safe(root / args.main)
        if not primary.is_file():
            raise ValueError("--main must identify an existing file inside --root")
        audit.scan(primary)
        audit.finish()
        exit_code = int(any(item["severity"] == "error" for item in audit.findings))
        report = audit.report()
    except (OSError, ValueError, RuntimeError) as exc:
        if audit is None:
            report = {"schema": "ml-paper-studio.tex-audit/1", "status": "needs_review",
                      "checks": {}, "findings": [], "scanned_files": [],
                      "limitations": ["Audit input was invalid; no successful static audit is claimed."]}
        else:
            report = audit.report()
        report["status"] = "needs_review"
        report["findings"].append({"severity": "error", "code": "invalid_audit_input",
                                   "file": None, "line": None, "message": str(exc)})
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            if audit is not None:
                aliases_input = args.output.resolve() in audit.files
                if not aliases_input and args.output.exists():
                    # resolve() catches symlinks; samefile() also compares the
                    # device/inode identity of differently named hard links.
                    aliases_input = any(args.output.samefile(path) for path in audit.files)
                if aliases_input:
                    raise OSError("output path would overwrite a scanned source/resource file")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        except OSError as exc:
            print("Could not save audit report: " + str(exc), file=sys.stderr)
            return 2
    sys.stdout.write(encoded)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
