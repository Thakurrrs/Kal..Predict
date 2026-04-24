"""Test suite for orchestrator with heartbeat loop and state recovery."""

import asyncio
import json
from pathlib import Path

import pytest

from kal_predict.config import AppConfig
from kal_predict.pipeline.orchestrator import Orchestrator
from kal_predict.trace import reset_trace_id, set_trace_id


@pytest.fixture
def config() -> AppConfig:
    """Load test configuration."""
    return AppConfig()


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary state directory for testing."""
    state_dir = tmp_path / "heartbeat"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


@pytest.fixture
def orchestrator(config: AppConfig, temp_state_dir: Path, monkeypatch):
    """Create Orchestrator instance with temporary state directory."""
    # Mock the state_dir property to use temp directory
    orchestrator_instance = Orchestrator(config)
    orchestrator_instance.state_dir = temp_state_dir
    orchestrator_instance.state_file = temp_state_dir / "state.json"
    return orchestrator_instance


class TestOrchestratorInitialization:
    """Tests for orchestrator initialization."""

    def test_orchestrator_initializes_state(self, config: AppConfig, temp_state_dir: Path):
        """Test that orchestrator initializes state directory."""
        orchestrator = Orchestrator(config)
        # Check that state_dir is created
        assert orchestrator.state_dir.exists()
        assert orchestrator.state_dir.is_dir()

    def test_orchestrator_initializes_empty_task_list(self, orchestrator: Orchestrator):
        """Test that orchestrator initializes with empty task list."""
        assert orchestrator.tasks == []

    def test_orchestrator_state_file_path(self, orchestrator: Orchestrator, temp_state_dir: Path):
        """Test that state_file path is set correctly."""
        assert orchestrator.state_file == orchestrator.state_dir / "state.json"


class TestHeartbeat:
    """Tests for heartbeat writing and reading."""

    @pytest.mark.asyncio
    async def test_orchestrator_writes_heartbeat(self, orchestrator: Orchestrator):
        """Test that orchestrator writes heartbeat to state file."""
        set_trace_id("test-trace-id-123")
        await orchestrator.write_heartbeat("task-1", "RUNNING")

        # Verify state file exists
        assert orchestrator.state_file.exists()

        # Verify state file contains correct data
        with open(orchestrator.state_file, "r") as f:
            state = json.load(f)

        assert state["task_id"] == "task-1"
        assert state["status"] == "RUNNING"
        assert state["trace_id"] == "test-trace-id-123"
        assert "timestamp" in state
        assert state["metadata"] == {}
        reset_trace_id()

    @pytest.mark.asyncio
    async def test_orchestrator_writes_heartbeat_with_metadata(self, orchestrator: Orchestrator):
        """Test that orchestrator writes heartbeat with metadata."""
        set_trace_id("test-trace-id-456")
        metadata = {"task_count": 5, "pending_count": 2}
        await orchestrator.write_heartbeat("task-2", "COMPLETE", metadata=metadata)

        with open(orchestrator.state_file, "r") as f:
            state = json.load(f)

        assert state["metadata"] == metadata
        reset_trace_id()

    @pytest.mark.asyncio
    async def test_orchestrator_reads_heartbeat(self, orchestrator: Orchestrator):
        """Test that orchestrator reads heartbeat from state file."""
        set_trace_id("test-trace-id-789")
        await orchestrator.write_heartbeat("task-3", "PENDING")

        state = await orchestrator.read_heartbeat()

        assert state is not None
        assert state["task_id"] == "task-3"
        assert state["status"] == "PENDING"
        assert state["trace_id"] == "test-trace-id-789"
        reset_trace_id()

    @pytest.mark.asyncio
    async def test_orchestrator_reads_heartbeat_missing_file(self, orchestrator: Orchestrator):
        """Test that read_heartbeat returns None if file doesn't exist."""
        state = await orchestrator.read_heartbeat()
        assert state is None

    @pytest.mark.asyncio
    async def test_orchestrator_reads_heartbeat_handles_io_error(self, orchestrator: Orchestrator):
        """Test that read_heartbeat gracefully handles I/O errors."""
        # Create a directory where the state file should be
        orchestrator.state_file.mkdir(parents=True, exist_ok=True)

        state = await orchestrator.read_heartbeat()
        assert state is None


class TestTaskQueue:
    """Tests for task queue management."""

    @pytest.mark.asyncio
    async def test_orchestrator_enqueue_task(self, orchestrator: Orchestrator):
        """Test that task is added to queue."""
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")

        assert len(orchestrator.tasks) == 1
        task = orchestrator.tasks[0]
        assert task["task_id"] == "task-1"
        assert task["task_type"] == "FORECAST"
        assert task["market_id"] == "WEATHER-001"
        assert task["status"] == "PENDING"
        assert "created_at" in task

    @pytest.mark.asyncio
    async def test_orchestrator_enqueue_multiple_tasks(self, orchestrator: Orchestrator):
        """Test that multiple tasks are added to queue."""
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")
        await orchestrator.enqueue_task("task-2", "FORECAST", "WEATHER-002")

        assert len(orchestrator.tasks) == 2

    @pytest.mark.asyncio
    async def test_orchestrator_claim_task(self, orchestrator: Orchestrator):
        """Test that task is marked as CLAIMED."""
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")

        claimed_task = await orchestrator.claim_task()

        assert claimed_task is not None
        assert claimed_task["task_id"] == "task-1"
        assert claimed_task["status"] == "CLAIMED"
        assert "claimed_at" in claimed_task

    @pytest.mark.asyncio
    async def test_orchestrator_claim_task_empty_queue(self, orchestrator: Orchestrator):
        """Test that claim_task returns None if queue is empty."""
        claimed_task = await orchestrator.claim_task()
        assert claimed_task is None

    @pytest.mark.asyncio
    async def test_orchestrator_claim_task_skips_non_pending(self, orchestrator: Orchestrator):
        """Test that claim_task only claims PENDING tasks."""
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")
        # Manually mark first task as CLAIMED
        orchestrator.tasks[0]["status"] = "CLAIMED"

        # Enqueue another task
        await orchestrator.enqueue_task("task-2", "FORECAST", "WEATHER-002")

        claimed_task = await orchestrator.claim_task()
        assert claimed_task["task_id"] == "task-2"

    @pytest.mark.asyncio
    async def test_orchestrator_complete_task(self, orchestrator: Orchestrator):
        """Test that task is marked COMPLETE."""
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")
        await orchestrator.claim_task()

        result = {"forecast": 0.65}
        await orchestrator.complete_task("task-1", result=result)

        task = orchestrator.tasks[0]
        assert task["status"] == "COMPLETE"
        assert "completed_at" in task
        assert task["result"] == result

    @pytest.mark.asyncio
    async def test_orchestrator_complete_task_without_result(self, orchestrator: Orchestrator):
        """Test that task can be completed without result."""
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")

        await orchestrator.complete_task("task-1")

        task = orchestrator.tasks[0]
        assert task["status"] == "COMPLETE"
        assert "completed_at" in task

    @pytest.mark.asyncio
    async def test_orchestrator_complete_task_not_found(self, orchestrator: Orchestrator):
        """Test that complete_task handles missing task gracefully."""
        # This should not raise an error
        await orchestrator.complete_task("nonexistent-task")

        # Task list should still be empty
        assert len(orchestrator.tasks) == 0


class TestCrashRecovery:
    """Tests for crash recovery functionality."""

    @pytest.mark.asyncio
    async def test_orchestrator_crash_recovery(self, orchestrator: Orchestrator):
        """Test that orchestrator reads last heartbeat on restart."""
        set_trace_id("test-trace-id-crash")
        await orchestrator.write_heartbeat("task-crashed", "RUNNING", metadata={"fail": True})

        # Create a new orchestrator instance (simulating restart)
        new_orchestrator = Orchestrator(AppConfig())
        new_orchestrator.state_dir = orchestrator.state_dir
        new_orchestrator.state_file = orchestrator.state_file

        last_state = await new_orchestrator.read_heartbeat()

        assert last_state is not None
        assert last_state["task_id"] == "task-crashed"
        assert last_state["metadata"]["fail"] is True
        reset_trace_id()


class TestHeartbeatLoop:
    """Tests for heartbeat loop functionality."""

    @pytest.mark.asyncio
    async def test_orchestrator_heartbeat_loop_runs(self, orchestrator: Orchestrator):
        """Test that heartbeat loop runs and writes heartbeats."""
        set_trace_id("test-trace-loop")

        # Run heartbeat loop for a short time
        loop_task = asyncio.create_task(orchestrator.heartbeat_loop(interval_seconds=0.1))

        # Let it run for a short time
        await asyncio.sleep(0.25)

        # Cancel the loop
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass

        # Verify that heartbeat was written
        state = await orchestrator.read_heartbeat()
        assert state is not None
        assert "task_count" in state["metadata"]
        reset_trace_id()

    @pytest.mark.asyncio
    async def test_orchestrator_heartbeat_loop_with_tasks(self, orchestrator: Orchestrator):
        """Test that heartbeat loop includes task counts in metadata."""
        set_trace_id("test-trace-loop-tasks")

        # Add some tasks
        await orchestrator.enqueue_task("task-1", "FORECAST", "WEATHER-001")
        await orchestrator.enqueue_task("task-2", "FORECAST", "WEATHER-002")

        # Run heartbeat loop briefly
        loop_task = asyncio.create_task(orchestrator.heartbeat_loop(interval_seconds=0.1))
        await asyncio.sleep(0.25)
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass

        # Verify heartbeat metadata includes task counts
        state = await orchestrator.read_heartbeat()
        assert state is not None
        assert state["metadata"]["task_count"] == 2
        assert state["metadata"]["pending_count"] == 2
        reset_trace_id()


class TestHeartbeatFormat:
    """Tests for heartbeat format and fields."""

    @pytest.mark.asyncio
    async def test_heartbeat_has_iso8601_timestamp(self, orchestrator: Orchestrator):
        """Test that heartbeat includes ISO8601 timestamp."""
        set_trace_id("test-timestamp")
        await orchestrator.write_heartbeat("task-1", "RUNNING")

        with open(orchestrator.state_file, "r") as f:
            state = json.load(f)

        # Check ISO8601 format (contains T and Z or +/-)
        assert "T" in state["timestamp"]
        reset_trace_id()

    @pytest.mark.asyncio
    async def test_heartbeat_pretty_printed_json(self, orchestrator: Orchestrator):
        """Test that heartbeat JSON is pretty-printed."""
        set_trace_id("test-pretty")
        await orchestrator.write_heartbeat("task-1", "RUNNING")

        with open(orchestrator.state_file, "r") as f:
            content = f.read()

        # Check for indentation (pretty-printing uses 2 spaces)
        assert "\n" in content
        assert "  " in content
        reset_trace_id()
