"""Command-line interface for Consilium.

    consilium research "electric vehicle charging market"   # run a full study
    consilium research "..." --json report.json --md report.md
    consilium runs                                          # list past runs
    consilium serve                                         # run the API
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from . import __version__
from .config import Settings
from .logging_setup import configure_logging
from .orchestration import ResearchRunner
from .reporting import to_json, to_markdown


def _print_progress(node: str, state) -> None:
    icon = {"plan": "🧭", "research": "🔎", "analyze": "🧩",
            "critique": "⚖️", "write": "📝"}.get(node, "•")
    last = state.critiques[-1] if state.critiques else None
    extra = f" score={last.score}" if node == "critique" and last else ""
    print(f"  {icon} {node:<9} status={state.status.value:<11} "
          f"sources={len(state.sources)} findings={len(state.findings)}{extra}", file=sys.stderr)


async def _research(args) -> int:
    settings = Settings.from_env()
    settings.max_iterations = args.max_iterations or settings.max_iterations
    configure_logging(settings.log_level, settings.log_json)
    runner = ResearchRunner(settings)

    print(f"\nResearching: {args.topic}  (provider={settings.provider}, search={settings.search_backend})\n",
          file=sys.stderr)
    state = None
    async for node, state in runner.stream(args.topic, depth=args.depth):
        _print_progress(node, state)

    if state is None or state.report is None:
        print("No report produced.", file=sys.stderr)
        return 1

    md = to_markdown(state.report)
    print("\n" + md)
    print(f"\n[run {state.run_id}] tokens={state.usage.total_tokens} "
          f"cost=${runner.cost_usd(state):.4f} iterations={state.iteration}", file=sys.stderr)

    if args.md:
        open(args.md, "w", encoding="utf-8").write(md)
        print(f"Markdown written to {args.md}", file=sys.stderr)
    if args.json_out:
        open(args.json_out, "w", encoding="utf-8").write(to_json(state.report))
        print(f"JSON written to {args.json_out}", file=sys.stderr)
    return 0


def _runs(args) -> int:
    runner = ResearchRunner(Settings.from_env())
    rows = runner.store.list()
    if not rows:
        print("No runs yet. Try: consilium research \"your topic\"")
        return 0
    for r in rows:
        print(f"  {r['id']}  {r['status']:<10} sources={r['sources']:<3} "
              f"findings={r['findings']:<3} tokens={r['prompt_tokens'] + r['completion_tokens']:<6} {r['topic']}")
    return 0


def _serve(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Install server extras: pip install 'consilium-research[server]'", file=sys.stderr)
        return 1
    uvicorn.run("consilium.service.api:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="consilium", description="Multi-agent corporate research system.")
    p.add_argument("--version", action="version", version=f"Consilium {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("research", help="run a research study")
    r.add_argument("topic")
    r.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")
    r.add_argument("--max-iterations", type=int, default=0)
    r.add_argument("--md", help="write the report as Markdown to this path")
    r.add_argument("--json", dest="json_out", help="write the report as JSON to this path")
    r.set_defaults(func=lambda a: asyncio.run(_research(a)))

    ls = sub.add_parser("runs", help="list past runs")
    ls.set_defaults(func=_runs)

    s = sub.add_parser("serve", help="run the FastAPI service")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")
    s.set_defaults(func=_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
