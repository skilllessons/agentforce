"""Worker — dequeues runs and executes the agent loop."""

from agentforge.platform.worker.loop import process_one, run_forever

__all__ = ["process_one", "run_forever"]
