"""Telemetry storage for Azure HayMaker CLI.

Manages JSON Lines storage of telemetry data with filtering, pruning, and export.
"""

import gzip
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TelemetryStorage:
    """Telemetry storage manager.

    Handles reading and writing telemetry data in JSON Lines format.
    """

    def __init__(self, storage_path: Path | str):
        """Initialize telemetry storage.

        Args:
            storage_path: Path to storage directory
        """
        self.storage_path = Path(storage_path) if isinstance(storage_path, str) else storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # File paths
        self._executions_file = self.storage_path / "executions.jsonl"
        self._agents_file = self.storage_path / "agents.jsonl"
        self._resources_file = self.storage_path / "resources.jsonl"
        self._last_sync_file = self.storage_path / "last_sync.txt"

    def save_executions(self, executions: List[Dict[str, Any]]) -> None:
        """Save execution records to storage (append mode).

        Args:
            executions: List of execution record dictionaries
        """
        self._append_jsonl(self._executions_file, executions)

    def save_agents(self, agents: List[Dict[str, Any]]) -> None:
        """Save agent records to storage (append mode).

        Args:
            agents: List of agent record dictionaries
        """
        self._append_jsonl(self._agents_file, agents)

    def save_resources(self, resources: List[Dict[str, Any]]) -> None:
        """Save resource records to storage (append mode).

        Args:
            resources: List of resource record dictionaries
        """
        self._append_jsonl(self._resources_file, resources)

    def load_executions(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Load execution records from storage.

        Args:
            filters: Optional filter criteria

        Returns:
            List of execution record dictionaries
        """
        records = self._read_jsonl(self._executions_file)
        if filters:
            records = self._apply_filters(records, filters)
        return records

    def load_agents(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Load agent records from storage.

        Args:
            filters: Optional filter criteria

        Returns:
            List of agent record dictionaries
        """
        records = self._read_jsonl(self._agents_file)
        if filters:
            records = self._apply_filters(records, filters)
        return records

    def load_resources(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Load resource records from storage.

        Args:
            filters: Optional filter criteria

        Returns:
            List of resource record dictionaries
        """
        records = self._read_jsonl(self._resources_file)
        if filters:
            records = self._apply_filters(records, filters)
        return records

    def get_date_range(self) -> Dict[str, Optional[datetime]]:
        """Get date range of stored execution data.

        Returns:
            Dictionary with earliest and latest timestamps
        """
        executions = self.load_executions()
        if not executions:
            return {"earliest": None, "latest": None}

        timestamps = []
        for exec_data in executions:
            if "started_at" in exec_data:
                try:
                    ts = self._parse_datetime(exec_data["started_at"])
                    if ts:
                        timestamps.append(ts)
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp for execution: {e}")
                    continue

        if not timestamps:
            return {"earliest": None, "latest": None}

        return {"earliest": min(timestamps), "latest": max(timestamps)}

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get timestamp of last telemetry sync.

        Returns:
            Last sync timestamp or None
        """
        if not self._last_sync_file.exists():
            return None

        try:
            with open(self._last_sync_file) as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.debug(f"Failed to read last sync time: {e}")
            return None

    def set_last_sync_time(self, timestamp: datetime) -> None:
        """Set timestamp of last telemetry sync.

        Args:
            timestamp: Sync timestamp
        """
        # Use os.open for atomic creation with secure permissions
        fd = os.open(str(self._last_sync_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(timestamp.isoformat())
        except Exception:
            os.close(fd)
            raise

    def prune_old_data(self, retention_days: int) -> Dict[str, int]:
        """Prune data older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Dictionary with count of records pruned per type
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Prune executions
        executions = self.load_executions()
        original_exec_count = len(executions)
        executions = [
            e
            for e in executions
            if self._parse_datetime(e.get("started_at", "")) and
            self._parse_datetime(e.get("started_at", "")) >= cutoff_date  # type: ignore
        ]
        self._write_jsonl(self._executions_file, executions)
        exec_pruned = original_exec_count - len(executions)

        # Prune agents
        agents = self.load_agents()
        original_agent_count = len(agents)
        agents = [
            a
            for a in agents
            if self._parse_datetime(a.get("started_at", "")) and
            self._parse_datetime(a.get("started_at", "")) >= cutoff_date  # type: ignore
        ]
        self._write_jsonl(self._agents_file, agents)
        agent_pruned = original_agent_count - len(agents)

        # Prune resources
        resources = self.load_resources()
        original_resource_count = len(resources)
        resources = [
            r
            for r in resources
            if self._parse_datetime(r.get("timestamp", "")) and
            self._parse_datetime(r.get("timestamp", "")) >= cutoff_date  # type: ignore
        ]
        self._write_jsonl(self._resources_file, resources)
        resource_pruned = original_resource_count - len(resources)

        return {
            "executions": exec_pruned,
            "agents": agent_pruned,
            "resources": resource_pruned,
        }

    def get_file_sizes(self) -> Dict[str, int]:
        """Get file sizes in bytes.

        Returns:
            Dictionary with file sizes
        """
        return {
            "executions": self._get_file_size(self._executions_file),
            "agents": self._get_file_size(self._agents_file),
            "resources": self._get_file_size(self._resources_file),
        }

    def compress_old_files(self, days_old: int = 7) -> List[Path]:
        """Compress files older than specified days.

        Args:
            days_old: Age threshold in days

        Returns:
            List of compressed file paths
        """
        compressed = []
        cutoff_time = datetime.utcnow().timestamp() - (days_old * 86400)

        for file_path in [self._executions_file, self._agents_file, self._resources_file]:
            if file_path.exists() and file_path.stat().st_mtime < cutoff_time:
                gz_path = Path(str(file_path) + ".gz")
                with open(file_path, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                compressed.append(gz_path)

        return compressed

    def vacuum(self) -> Dict[str, Any]:
        """Vacuum storage: remove duplicates and compact files.

        Returns:
            Dictionary with vacuum results
        """
        records_removed = 0

        # Vacuum executions (remove duplicates by ID)
        executions = self.load_executions()
        unique_executions = self._deduplicate_by_id(executions)
        removed = len(executions) - len(unique_executions)
        records_removed += removed
        self._write_jsonl(self._executions_file, unique_executions)

        # Vacuum agents
        agents = self.load_agents()
        unique_agents = self._deduplicate_by_id(agents)
        removed = len(agents) - len(unique_agents)
        records_removed += removed
        self._write_jsonl(self._agents_file, unique_agents)

        # Vacuum resources
        resources = self.load_resources()
        unique_resources = self._deduplicate_by_id(resources)
        removed = len(resources) - len(unique_resources)
        records_removed += removed
        self._write_jsonl(self._resources_file, unique_resources)

        return {"success": True, "records_removed": records_removed}

    def export_to_json(self, export_file: Path) -> None:
        """Export all data to JSON file with secure permissions.

        Args:
            export_file: Path to export file
        """
        data = {
            "executions": self.load_executions(),
            "agents": self.load_agents(),
            "resources": self.load_resources(),
        }

        # Use os.open for atomic creation with secure permissions
        fd = os.open(str(export_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            os.close(fd)
            raise

    def import_from_json(self, import_file: Path) -> None:
        """Import data from JSON file.

        Args:
            import_file: Path to import file
        """
        with open(import_file) as f:
            data = json.load(f)

        if "executions" in data:
            self.save_executions(data["executions"])
        if "agents" in data:
            self.save_agents(data["agents"])
        if "resources" in data:
            self.save_resources(data["resources"])

    # Private methods

    def _append_jsonl(self, file_path: Path, records: List[Dict[str, Any]]) -> None:
        """Append records to JSON Lines file with secure permissions."""
        # Use os.open for atomic creation with secure permissions
        fd = os.open(str(file_path), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        try:
            with os.fdopen(fd, "a") as f:
                for record in records:
                    f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            os.close(fd)
            raise

    def _write_jsonl(self, file_path: Path, records: List[Dict[str, Any]]) -> None:
        """Write records to JSON Lines file (overwrite) with secure permissions."""
        # Use os.open for atomic creation with secure permissions
        fd = os.open(str(file_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                for record in records:
                    f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            os.close(fd)
            raise

    def _read_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read records from JSON Lines file."""
        if not file_path.exists():
            return []

        records = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping corrupted line in {file_path.name}: {e}")
                    continue

        return records

    def _apply_filters(
        self, records: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to records."""
        filtered = records

        # Filter by exact field matches
        for key, value in filters.items():
            if key in ["start_date", "end_date"]:
                continue
            filtered = [r for r in filtered if r.get(key) == value]

        # Filter by date range
        if "start_date" in filters:
            start_date = self._parse_datetime(filters["start_date"])
            if start_date:
                filtered = [
                    r
                    for r in filtered
                    if self._parse_datetime(r.get("started_at") or r.get("timestamp", ""))
                    and self._parse_datetime(r.get("started_at") or r.get("timestamp", ""))
                    >= start_date  # type: ignore
                ]

        if "end_date" in filters:
            end_date = self._parse_datetime(filters["end_date"])
            if end_date:
                filtered = [
                    r
                    for r in filtered
                    if self._parse_datetime(r.get("started_at") or r.get("timestamp", ""))
                    and self._parse_datetime(r.get("started_at") or r.get("timestamp", ""))
                    <= end_date  # type: ignore
                ]

        return filtered

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from string or datetime object."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception as e:
                logger.debug(f"Failed to parse datetime '{value}': {e}")
                return None
        return None

    def _get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        return file_path.stat().st_size if file_path.exists() else 0

    def _deduplicate_by_id(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate records by ID (keep last)."""
        seen = {}
        for record in records:
            record_id = record.get("id")
            if record_id:
                seen[record_id] = record

        return list(seen.values())
