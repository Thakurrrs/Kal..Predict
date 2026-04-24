"""Orchestrator for heartbeat loop and state recovery."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kal_predict.config import AppConfig
from kal_predict.trace import get_trace_id

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrator for managing heartbeat loop and task state."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize orchestrator with state directory.

        Args:
            config: Application configuration
        """
        self.config = config
        # Determine project root from file location
        project_root = Path(__file__).parent.parent.parent.parent
        self.state_dir = project_root / "data" / "heartbeat"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self.tasks: List[Dict[str, Any]] = []
        logger.info(f"Orchestrator initialized. State dir: {self.state_dir}")

    async def write_heartbeat(
        self, task_id: str, status: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Write heartbeat to state file.

        Args:
            task_id: Task identifier
            status: Task status
            metadata: Optional metadata dictionary

        """
        state = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": get_trace_id(),
            "task_id": task_id,
            "status": status,
            "metadata": metadata or {},
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"Heartbeat written: {task_id} → {status}")
        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")

    async def read_heartbeat(self) -> Optional[Dict[str, Any]]:
        """Read heartbeat from state file.

        Returns:
            Parsed state dictionary or None if file doesn't exist

        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
            logger.info(f"Heartbeat read: {state.get('task_id')} → {state.get('status')}")
            return state
        except Exception as e:
            logger.error(f"Failed to read heartbeat: {e}")
            return None

    async def enqueue_task(self, task_id: str, task_type: str, market_id: str) -> None:
        """Enqueue task to task list.

        Args:
            task_id: Task identifier
            task_type: Type of task (e.g., FORECAST)
            market_id: Market identifier

        """
        task: Dict[str, Any] = {
            "task_id": task_id,
            "task_type": task_type,
            "market_id": market_id,
            "created_at": datetime.now().isoformat(),
            "status": "PENDING",
        }
        self.tasks.append(task)
        logger.info(f"Task enqueued: {task_id} ({task_type} for {market_id})")

    async def claim_task(self) -> Optional[Dict[str, Any]]:
        """Claim first pending task from queue.

        Returns:
            Claimed task or None if queue is empty

        """
        for task in self.tasks:
            if task["status"] == "PENDING":
                task["status"] = "CLAIMED"
                task["claimed_at"] = datetime.now().isoformat()
                logger.info(f"Task claimed: {task['task_id']}")
                return task

        logger.info("No pending tasks to claim")
        return None

    async def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as complete.

        Args:
            task_id: Task identifier
            result: Optional result dictionary

        """
        for task in self.tasks:
            if task["task_id"] == task_id:
                task["status"] = "COMPLETE"
                task["completed_at"] = datetime.now().isoformat()
                if result is not None:
                    task["result"] = result
                logger.info(f"Task completed: {task_id}")
                return

        logger.warning(f"Task not found for completion: {task_id}")

    async def heartbeat_loop(self, interval_seconds: int = 15) -> None:
        """Run heartbeat loop continuously.

        Args:
            interval_seconds: Interval in seconds between heartbeats

        """
        logger.info(f"Starting heartbeat loop (interval: {interval_seconds}s)")

        # Check for last heartbeat (crash recovery)
        last_state = await self.read_heartbeat()
        if last_state:
            logger.info(f"Recovered last heartbeat: task={last_state.get('task_id')}")

        while True:
            try:
                # Count tasks by status
                pending_count = sum(1 for task in self.tasks if task["status"] == "PENDING")
                claimed_count = sum(1 for task in self.tasks if task["status"] == "CLAIMED")
                complete_count = sum(1 for task in self.tasks if task["status"] == "COMPLETE")

                metadata = {
                    "task_count": len(self.tasks),
                    "pending_count": pending_count,
                    "claimed_count": claimed_count,
                    "complete_count": complete_count,
                }

                await self.write_heartbeat("heartbeat", "RUNNING", metadata=metadata)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                raise
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(interval_seconds)
