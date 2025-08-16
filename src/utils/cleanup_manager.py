"""Cleanup manager for organizing test logs and analysis files."""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict
import re


class CleanupStats(TypedDict):
    """Statistics from cleanup operations."""

    status: str
    files_moved: int
    files_deleted: int
    duplicates_removed: int
    files_archived: int


class CleanupManager:
    """Manages cleanup of test logs and redundant files."""

    @staticmethod
    def clean_analysis_directory(analysis_dir: Path) -> CleanupStats:
        """
        Clean up an analysis directory to match the expected structure.

        Args:
            analysis_dir: Path to the analysis directory

        Returns:
            Dictionary with cleanup statistics
        """
        if not analysis_dir.exists():
            return CleanupStats(
                status="not_found",
                files_moved=0,
                files_deleted=0,
                duplicates_removed=0,
                files_archived=0,
            )

        stats = {"files_moved": 0, "files_deleted": 0, "duplicates_removed": 0}

        # Expected structure
        expected_root_files = {
            "analysis.md",
            "metadata.json",
            "reviewer_feedback.json",
            "iteration_history.json",
        }

        # Move iteration files to iterations/ directory
        iterations_dir = analysis_dir / "iterations"
        iterations_dir.mkdir(exist_ok=True)

        # Pattern for iteration files that should be in iterations/
        iteration_patterns = [
            re.compile(r"iteration_\d+\.md$"),
            re.compile(r"feedback_\d+\.json$"),
            re.compile(r"analysis_iteration_\d+.*\.md$"),
            re.compile(r"reviewer_feedback_iteration_\d+\.json$"),
        ]

        # Process all files in root
        for file in analysis_dir.iterdir():
            # Skip directories and broken symlinks
            if file.is_dir():
                continue

            # Handle symlinks
            if file.is_symlink():
                # Remove broken symlinks
                if not file.exists():
                    file.unlink()
                    stats["files_deleted"] += 1
                    continue
                # Skip working symlinks for now
                continue

            if file.is_file():
                # Check if this is an iteration file that should be moved
                for pattern in iteration_patterns:
                    if pattern.match(file.name):
                        # Move to iterations directory
                        target = iterations_dir / file.name
                        if not target.exists():
                            _ = shutil.move(str(file), str(target))
                            stats["files_moved"] += 1
                        else:
                            # Duplicate - delete the root one
                            file.unlink()
                            stats["duplicates_removed"] += 1
                        break

                # Check for old timestamped files
                if "_20" in file.name and file.name not in expected_root_files:
                    # This looks like an old timestamped file
                    archive_dir = analysis_dir / ".archive" / "migrated_old_files"
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    _ = shutil.move(str(file), str(archive_dir / file.name))
                    stats["files_moved"] += 1

        # Clean up duplicate feedback files
        # If we have both reviewer_feedback.json and reviewer_feedback_iteration_1.json in iterations/
        feedback_file = analysis_dir / "reviewer_feedback.json"
        iter_feedback = iterations_dir / "reviewer_feedback_iteration_1.json"
        if feedback_file.exists() and iter_feedback.exists():
            # Keep the one in iterations/, update the root
            _ = shutil.copy2(str(iter_feedback), str(feedback_file))
            stats["duplicates_removed"] += 1

        return CleanupStats(
            status="cleaned",
            files_moved=stats["files_moved"],
            files_deleted=stats["files_deleted"],
            duplicates_removed=stats["duplicates_removed"],
            files_archived=0,
        )

    @staticmethod
    def organize_test_logs(
        logs_dir: Path, max_logs_per_test: int = 3
    ) -> dict[str, Any]:
        """
        Organize and archive test logs, keeping only recent ones.

        Args:
            logs_dir: Path to logs/test directory
            max_logs_per_test: Maximum number of logs to keep per test type

        Returns:
            Dictionary with cleanup statistics
        """
        if not logs_dir.exists():
            return {"status": "not_found"}

        stats = {"files_archived": 0, "files_deleted": 0, "tests_organized": 0}

        # Create archive directory
        archive_dir = logs_dir / ".archive"
        archive_dir.mkdir(exist_ok=True)

        # Group logs by test type (e.g., "1_debug_AI-powered_fitness_app")
        test_groups = {}
        pattern = re.compile(r"^(\d+_\w+_[^_]+(?:_[^_]+){0,3})_\d{8}_\d{6}\.log$")

        for log_file in logs_dir.glob("*.log"):
            match = pattern.match(log_file.name)
            if match:
                test_name = match.group(1)
                if test_name not in test_groups:
                    test_groups[test_name] = []
                test_groups[test_name].append(log_file)

        # Process each test group
        for test_name, log_files in test_groups.items():
            # Sort by modification time (newest first)
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            if len(log_files) > max_logs_per_test:
                stats["tests_organized"] += 1

                # Keep the newest N logs
                # to_keep = log_files[:max_logs_per_test]  # Currently unused but may be needed for future logging
                to_archive = log_files[max_logs_per_test:]

                # Archive old logs
                test_archive = archive_dir / test_name
                test_archive.mkdir(exist_ok=True)

                for old_log in to_archive:
                    target = test_archive / old_log.name
                    _ = shutil.move(str(old_log), str(target))
                    stats["files_archived"] += 1

        # Clean up archives older than 7 days
        cutoff_time = datetime.now() - timedelta(days=7)
        for archived_dir in archive_dir.iterdir():
            if archived_dir.is_dir():
                for old_file in archived_dir.iterdir():
                    if old_file.stat().st_mtime < cutoff_time.timestamp():
                        old_file.unlink()
                        stats["files_deleted"] += 1

        return stats

    @staticmethod
    def clean_all_analyses(base_dir: Path) -> dict[str, Any]:
        """
        Clean all analysis directories.

        Args:
            base_dir: Path to analyses directory

        Returns:
            Combined statistics
        """
        if not base_dir.exists():
            return {"status": "not_found"}

        total_stats = {
            "directories_cleaned": 0,
            "total_files_moved": 0,
            "total_duplicates_removed": 0,
        }

        for analysis_dir in base_dir.iterdir():
            if analysis_dir.is_dir() and not analysis_dir.name.startswith("."):
                stats = CleanupManager.clean_analysis_directory(analysis_dir)
                if (
                    stats.get("files_moved", 0) > 0
                    or stats.get("duplicates_removed", 0) > 0
                ):
                    total_stats["directories_cleaned"] += 1
                    total_stats["total_files_moved"] += stats.get("files_moved", 0)
                    total_stats["total_duplicates_removed"] += stats.get(
                        "duplicates_removed", 0
                    )

        return total_stats
