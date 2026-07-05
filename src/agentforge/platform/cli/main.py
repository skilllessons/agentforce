"""CLI entry point.

    agentforge run --vertical insurance --query "..." [--dry-run]

Enqueues a run and prints the run_id. For Sunday's milestone, a separate
worker process drains the queue; later we may add a --wait flag that polls
runs.get until the status is terminal.
"""

from __future__ import annotations

import argparse
import asyncio

from nanoid import generate as nanoid

from agentforge.platform.run_orchestrator.queue import enqueue_run


def _build_parser() -> argparse.ArgumentParser:
    """Define the `agentforge run` subcommand and its flags."""
    parser = argparse.ArgumentParser(prog="agentforge")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="enqueue a research run")
    run.add_argument("--vertical", required=True)
    run.add_argument("--query", required=True)
    run.add_argument("--tenant", default="local-dev")
    run.add_argument("--dry-run", action="store_true")

    return parser


async def _run(args: argparse.Namespace) -> None:
    """Generate a run_id, enqueue it, print it. --dry-run skips the enqueue."""
    run_id = nanoid(size=12)
    if args.dry_run:
        print(f"[dry-run] would enqueue {run_id}: "
              f"vertical={args.vertical} tenant={args.tenant} query={args.query!r}")

        return
    await enqueue_run(
        run_id,
        tenant_id=args.tenant,
        vertical=args.vertical,
        query=args.query,
    )
    print(run_id)


def main() -> None:
    """Sync entry point referenced by the console_script in pyproject.toml."""
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
