"""Render a :class:`~consilium.models.Report` to Markdown or JSON."""

from __future__ import annotations

import json

from .models import Report


def to_markdown(report: Report) -> str:
    lines = [f"# Research report: {report.topic}", "", "## Executive summary", "",
             report.executive_summary, ""]

    # Stable citation numbering across the whole report.
    numbering = {s.id: i + 1 for i, s in enumerate(report.sources)}

    for section in report.sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        lines.append(section.content)
        if section.citations:
            refs = ", ".join(f"[{numbering.get(sid, '?')}]" for sid in section.citations)
            lines.append("")
            lines.append(f"_Sources: {refs}_")
        lines.append("")

    if report.sources:
        lines.append("## References")
        lines.append("")
        for i, s in enumerate(report.sources, 1):
            lines.append(f"{i}. [{s.title}]({s.url})")
    return "\n".join(lines).strip() + "\n"


def to_json(report: Report, indent: int | None = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent, ensure_ascii=False)
