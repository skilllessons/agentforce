"""CLI entry point.

    agentforge run --vertical insurance --query "..." [--dry-run]
    agentforge issue-key --tenant local-dev [--name "studio dev"]

Enqueues a run and prints the run_id. For Sunday's milestone, a separate
worker process drains the queue; later we may add a --wait flag that polls
runs.get until the status is terminal.

issue-key mints an API key for a tenant and prints it once — the plaintext is
never stored, so a lost key is reissued, not recovered.
"""

from __future__ import annotations

import argparse
import asyncio

from nanoid import generate as nanoid

from agentforge.core.auth.keys import issue_key
from agentforge.platform.run_orchestrator.queue import enqueue_run


def _build_parser() -> argparse.ArgumentParser:
    """Define the `agentforge` subcommands and their flags."""
    parser = argparse.ArgumentParser(prog="agentforge")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="enqueue a research run")
    run.add_argument("--vertical", required=True)
    run.add_argument("--query", required=True)
    run.add_argument("--tenant", default="local-dev")
    run.add_argument("--dry-run", action="store_true")

    key = sub.add_parser("issue-key", help="mint an API key for a tenant")
    key.add_argument("--tenant", default="local-dev")
    key.add_argument("--name", default=None, help="label for this key")

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


async def _issue_key(args: argparse.Namespace) -> None:
    """Mint a key for a tenant and print it. Printed once — never recoverable."""
    key = await issue_key(args.tenant, name=args.name)
    print(key)


def main() -> None:
    """Sync entry point referenced by the console_script in pyproject.toml."""
    parser = _build_parser()
    args = parser.parse_args()
    handler = _issue_key if args.command == "issue-key" else _run
    asyncio.run(handler(args))


if __name__ == "__main__":
    main()
