# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
r""" verification.py

Project git repo verification & reports model
"""
import json
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict, Iterable, overload
from .file_changes import filter_changes, is_synced, FileChanges, ChangeTypes

REPORT_DIR = Path("font/cover")


class Source(StrEnum):
    """
    Determined source state for an updated Unicode project.

    :cvar ASE: :code:`aseprite`: Aseprite is the source.
    :cvar PNG: :code:`png`: PNG design sheets are the source.
    :cvar PBM: :code:`pbm`: PBM files changed without a source design;
                the source is undetermined in this case.
    """
    ASE = "aseprite"
    PNG = "png"
    PBM = "pbm"


SaveStatus = Literal["synced", "updated"]
"""
Final status will either be synced (no file changed) or updated, 
updated file are the newly saved files generated from the save's determined source.
"""


class ProjectReport(TypedDict):
    status: SaveStatus
    source: Literal[Source.PNG, Source.PBM, Source.ASE]
    update: FileChanges[str]


class SavesReport(TypedDict):
    """
    Final report data, savable as::

    saves-base[:7]-head[:7].json

    Or parsed as .html viewable document.
    """
    base: str
    head: str
    status: SaveStatus
    projects: dict[str, ProjectReport]


class VerificationReport:
    """
    Methods::

    add_project(block_name, source, changes)

    write_json()

    write_html(magic, token)

    :ivar data: Embed JSON serializable data of the final report.
    """

    def __init__(self, base: str, head: str) -> None:
        self.data: SavesReport = {
            "base": base,
            "head": head,
            "status": "synced",
            "projects": {},
        }

    def add_project(
        self,
        block_name: str,
        source: Source,
        changes: FileChanges | None = None,
    ) -> None:
        if source is Source.PBM:
            project: ProjectReport = {
                "status": "updated",
                "source": Source.PBM,
                "update": {
                    "added": [],
                    "unsync": [],
                    "modified": [],
                },
            }

        else:
            assert changes is not None

            project: ProjectReport = {
                "status": "synced" if is_synced(changes) else "updated",
                "source": source,
                "update": changes
            }

        self.data["projects"][block_name] = project

        if project["status"] == "updated":
            self.data["status"] = project["status"]

    def write_json(self):
        return self._write_report("json")

    def write_html(self, *,
                   magic: str | None=None,
                   token: str | None=None) -> Path:
        return self._write_report("html", magic=magic, token=token)

    @overload
    def _write_report(self, option: Literal["json"], *,
                     magic: None=None, token: None=None) -> Path: ...

    @overload
    def _write_report(self, option: Literal["html"], *,
                     magic: str | None=None, token: str | None=None) -> Path: ...

    def _write_report(self, option: Literal["json", "html"], *,
                     magic: str | None=None,
                     token: str | None=None) -> Path:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        base: str = self.data["base"]
        head: str = self.data["head"]

        if option == "json":
            path = REPORT_DIR / f"saves-{base[:7]}-{head[:7]}.json"

            with path.open("w", encoding="utf-8") as io:
                json.dump(self.data, io, indent=2, ensure_ascii=False,)
                io.write("\n")
            print(f"Wrote Reports: \33[33m\033[1m{path}\033[0m")
        elif option == "html":
            html = self._report_html(magic=magic, token=token)

            path = REPORT_DIR / f"saves-{base[:7]}-{head[:7]}.html"
            path.write_text(html, encoding="utf-8")
            print(f"Wrote Reports: \33[33m\033[1m{path}\033[0m")
        else:
            raise ValueError(f"Unsupported report format: {option}")

        return path

    def _report_html(self, *,
                     magic: str | None=None,
                     token: str | None=None) -> str:
        data: SavesReport = self.data
        projects: dict[str, ProjectReport] = data["projects"]

        # All possible title status
        has_missing_source: bool = any(
            project["source"] is Source.PBM
            for project in projects.values()
        )

        has_updates: bool = data["status"] == "updated"

        if has_missing_source:
            title = "⚠ MISSING SOURCE"
            title_message = (
                "Some bitmap files were changed without a  source design. "
                "These changes cannot be verified automatically."
            )
        elif has_updates:
            title = "🟡 OUT OF SYNC"
            title_message = (
                "There are generated files that need to be synchronized "
                "with their determined source files."
            )
        else:
            title = "✅ SYNCED"
            title_message = (
                "All generated design files are synchronized with their "
                "source files."
            )

        # Helpers
        def escape(s: str):
            """:return: Escape "&", "<" and ">" to HTML-safe sequences."""
            s = s.replace("&", "&amp;")
            s = s.replace("<", "&lt;")
            s = s.replace(">", "&gt;")
            return s

        def source_name(source_type: Source) -> str:
            """:return: label naming for each :class:`Source`"""
            return {
                Source.PNG: "PNG Sheet",
                Source.ASE: "Aseprite",
                Source.PBM: "<strong>⚠ MISSING SOURCE</strong>",
            }[source_type]

        def pbm_files(changes: FileChanges[str]) -> list[str]:
            """:return: Collected .pbm files inside :class:`FileChanges`"""
            return sorted(path for path in (
                set(changes["added"]) | set(changes["unsync"]) | set(changes["modified"])
            ) if path.endswith(".pbm"))

        def project_source_files(project: str, changes: FileChanges[str]) -> FileChanges[Path]:
            """:return: Sort as relative file names for simplicity and omit .pbm files"""
            root: str = f"projects/{project}"
            return {
                "modified": sorted({
                    Path(path).relative_to(root)
                    for path in changes["modified"]
                    if path.endswith(".png") or path.endswith(".aseprite")
                }, reverse=True),
                "added": sorted({
                    Path(path).relative_to(root)
                    for path in changes["added"]
                    if path.endswith(".png") or path.endswith(".aseprite")
                }, reverse=True),
                "unsync": sorted({
                    Path(path).relative_to(root)
                    for path in changes["unsync"]
                    if path.endswith(".png") or path.endswith(".aseprite")
                }, reverse=True),
            }

        # Project status table
        rows: list[str] = []
        bitmap_count: int = 0
        source_count: int = 0
        t: str = "style=\"padding: 8px; border: 1px solid;\""
        """Simplest table cells' style 8px padding & 1px border."""

        for block_name, project in projects.items():
            block: str = escape(block_name)
            source = project["source"]

            # PBM-only source will be flagged as missing
            if source is Source.PBM:
                rows.append("<tr>")
                rows.append(f"  <td {t}>{block}</td>")
                rows.append(f"  <td {t}>{source_name(source)}</td>")
                rows.append(f"  <td colspan=\"3\" {t}>")
                rows.append("    Bitmap (<code>.pbm</code>) files were changed without")
                rows.append("    a PNG or Aseprite source.<br/>")
                rows.append("    Modify the PNG design sheets or")
                rows.append("    <code>design.aseprite</code> instead of modifying")
                rows.append("    generated PBM files directly.")
                rows.append("  </td>")
                rows.append("</tr>")
                continue

            # Normal .png/.aseprite sources
            sources: FileChanges[Path] = project_source_files(block_name, project["update"])
            pbm_len: int = len(pbm_files(project["update"]))
            types: Iterable[ChangeTypes] = sources.keys()

            size = { change: len(sources[change]) for change in types }
            source_count += sum(size.values())
            bitmap_count += pbm_len

            row_span: int = max(size.values())
            rows.append(f"<tr>")
            rows.append(f"  <td rowspan=\"{max(row_span, 1)}\" {t}>{block}</td>")
            rows.append(f"  <td rowspan=\"{max(row_span, 1)}\" {t}>{source_name(source)}</td>")

            # Nothing source-visible changed. This can happen when the only
            # canonical differences are generated PBM files.
            if is_synced(sources):
                if pbm_len > 0:
                    rows.append(f"  <td colspan=\"3\" {t}>{pbm_len} Bitmap (.pbm) files not synced</td>")
                rows.append(f"</tr>")
                continue

            # Either one of the change list will fully fill row span
            spans: dict[ChangeTypes, int] = { change: row_span for change in types }

            def td_cell(index: int, name: Path | None, check_type: ChangeTypes) -> str | None:
                if name is not None:
                    spans[check_type] -= 1
                    return f"  <td {t}><code>{escape(str(name))}</code></td>"

                if (span := spans[check_type]) > 0:
                    # Index 0 to display label if its synced (size is 0)
                    if index == 0 and size[check_type] == 0:
                        spans[check_type] -= 1
                        return f"  <td {t}>✅ None</td>"

                    spans[check_type] -= span
                    return f"  <td rowspan=\"{span}\" {t}><br/></td>"
                return None

            for i in range(row_span):
                if i > 0:
                    rows.append(f"<tr>")

                # Check all types and fill them in cell index
                for check in types:
                    file = sources[check].pop() if i < size[check] else None
                    if cell := td_cell(i, file, check):
                        rows.append(cell)

                rows.append(f"</tr>")

        # Sync section, if updated
        base: str = escape(data["base"][:7])
        head: str = escape(data["head"][:7])

        if has_updates:
            sync: list[str] = [
                "<h3>🟡 Sync Required</h3>",
                "<p>Generated files are out of sync with their source designs.</p>",
                ("<p>"
                 f" ➜ Pending: <strong>{source_count} Source files</strong> +"
                 f" <strong>{bitmap_count} Bitmap (.pbm) files</strong><br/>"),
            ]

            if isinstance(token, str):
                # If we have a placeholder token, it is assumed to be the patch file's href to share
                sync.append("  You can synchronize them by applying the generated patch:<br/>")
                sync.append("</p>")
                sync.append("<p>")
                sync.append(
                    f"  <strong>Patch file:</strong> "
                    f"<a href=\"{token}\">sync-{base}-{head}.patch</a>")
                sync.append("</p>")
                sync.append(f"<pre><code>git apply sync-{base}-{head}.patch</code></pre>")
            else:
                sync.append("</p>")

        else:
            sync: list[str] = [""]

        # Final report
        doctype: str = "<!DOCTYPE html>\n<html lang=\"en\">"
        html: str = f"<!-- {magic} -->\n{doctype}" if isinstance(magic, str) else doctype

        return (
        f"{html}\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "</head>\n"
        "<body>\n"
        f"  <h2>Status: {title}</h2>\n"
        f"  <p>{title_message}</p>\n"
        "  <table style=\"border-collapse: collapse;\">\n"
        "    <caption>Updated Unicode Blocks</caption>\n"
        "    <thead>\n"
        "      <tr>\n"
        f"        <th rowspan=\"2\" {t}>Unicode Block</th>\n"
        f"        <th rowspan=\"2\" {t}>Source</th>\n"
        f"        <th colspan=\"3\" {t}>Sync</th>\n"
        "      </tr>\n"
        "      <tr>\n"
        f"        <th {t}>Modified</th>\n"
        f"        <th {t}>Added</th>\n"
        f"        <th {t}>Unsync</th>\n"
        "      </tr>\n"
        "    </thead>\n"
        "    <tbody>\n"
        f"      {"\n      ".join(rows)}\n"
        "    </tbody>\n"
        "  </table>\n"
        f"  {"\n      ".join(sync)}\n"
        "  <p>\n"
        "    <strong>Verified commit:</strong>\n"
        f"    <code>{head}</code>\n"
        "  </p>\n"
        "</body>\n"
        "</html>\n")
