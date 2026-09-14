"""Run the local UI or reproduce the complete agent from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_env
from .fixtures import DEMO_INPUT
from .providers import ProviderError
from .validation import ValidationError
from .workflow import ResearchAgent


def save_report(report, directory):
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    (target / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (target / "report.md").write_text(report["markdown"], encoding="utf-8")
    (target / "references.bib").write_text(report["bibtex"], encoding="utf-8")
    print(f"Saved {len(report['papers'])} papers → {target.resolve()}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scholar Compass — plan, discover, rank, verify.")
    commands = parser.add_subparsers(dest="command", required=True)
    ui = commands.add_parser("serve", help="Start the local web UI")
    ui.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8000)
    demo = commands.add_parser("demo", help="Reproduce the offline RAG example without credentials")
    demo.add_argument("--output", default="runs/demo")
    for name in ("plan", "run"):
        sub = commands.add_parser(name, help="Create a plan" if name == "plan" else "Execute a research request")
        sub.add_argument("--input", required=True, type=Path, help="Input JSON; optional embedded reviewed plan")
        sub.add_argument("--output", default="runs/plan.json" if name == "plan" else "runs/research")
    args = parser.parse_args(argv)
    load_env()
    try:
        if args.command == "serve":
            from .server import serve
            serve(args.host, args.port)
            return 0
        agent = ResearchAgent()
        data = DEMO_INPUT if args.command == "demo" else json.loads(args.input.read_text(encoding="utf-8"))
        if args.command == "plan":
            plan = agent.plan(data)
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Saved reading plan → {target.resolve()}")
        else:
            save_report(agent.run(data), args.output)
        return 0
    except (OSError, ValueError, ValidationError, ProviderError) as exc:
        # ProviderError is already sanitized; never dump a stack containing API credentials.
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
