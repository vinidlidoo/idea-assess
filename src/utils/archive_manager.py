"""Archive manager for organizing and cleaning up analysis files."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import TypedDict
import re


class ArchiveMetadata(TypedDict, total=False):
    """Metadata for archived runs."""

    archived_at: str
    run_type: str
    run_number: int
    created_at: str
    final_status: str
    iteration_count: int
    word_count: int
    character_count: int
    reviewer_decision: str
    critical_issues: int
    improvements: int
    assessment: str
    iterations: list[dict[str, object]]


class ArchiveSummaryItem(TypedDict):
    """Single archive summary item."""

    name: str
    run_type: str
    archived_at: str
    run_number: int


class ArchiveSummary(TypedDict):
    """Summary of all archives."""

    archives: list[ArchiveSummaryItem]
    total: int
    test_runs: int
    production_runs: int


class ArchiveManager:
    """Manages archiving and cleanup of analysis files."""

    max_archives: int
    archive_test_runs: bool

    def __init__(self, max_archives: int = 5, archive_test_runs: bool = True):
        """
        Initialize the archive manager.

        Args:
            max_archives: Maximum number of archived runs to keep
            archive_test_runs: Whether to archive test runs separately
        """
        self.max_archives = max_archives
        self.archive_test_runs = archive_test_runs

    def archive_current_analysis(
        self,
        analysis_dir: Path,
        run_type: str = "production",
        metadata: ArchiveMetadata | None = None,
    ) -> Path | None:
        """
        Archive the current analysis files before creating new ones.

        Args:
            analysis_dir: Directory containing the analysis
            run_type: Type of run ("test", "production", "debug")
            metadata: Additional metadata to store

        Returns:
            Path to the archive directory, or None if nothing to archive
        """

        if not analysis_dir.exists():
            return None

        # Check if there's anything to archive
        analysis_file = analysis_dir / "analysis.md"

        if not analysis_file.exists() or analysis_file.is_symlink():
            # If it's a symlink, we're still using old structure
            self._migrate_old_structure(analysis_dir)
            return None

        # Create archive directory
        archive_base = analysis_dir / ".archive"
        archive_base.mkdir(exist_ok=True)

        # Generate archive name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_number = self._get_next_run_number(archive_base, run_type)
        archive_name = f"{run_type}_{run_number:03d}_{timestamp}"
        archive_dir = archive_base / archive_name
        archive_dir.mkdir(exist_ok=True)

        # Move current files to archive
        files_to_archive = [
            "analysis.md",
            "metadata.json",
            "reviewer_feedback.json",
            "iteration_history.json",
        ]

        for filename in files_to_archive:
            source = analysis_dir / filename
            if source.exists() and not source.is_symlink():
                _ = shutil.move(str(source), str(archive_dir / filename))

        # Archive iteration files
        iterations_dir = analysis_dir / "iterations"
        if iterations_dir.exists():
            _ = shutil.move(str(iterations_dir), str(archive_dir / "iterations"))

        # Save archive metadata
        archive_metadata: ArchiveMetadata = {
            "archived_at": datetime.now().isoformat(),
            "run_type": run_type,
            "run_number": run_number,
            **(metadata or {}),
        }

        with open(archive_dir / "archive_metadata.json", "w") as f:
            json.dump(archive_metadata, f, indent=2)

        # Clean up old archives
        self._cleanup_old_archives(archive_base)

        return archive_dir

    def _migrate_old_structure(self, analysis_dir: Path):
        """
        Migrate from old timestamped structure to new clean structure.

        Args:
            analysis_dir: Directory to migrate
        """

        # Create archive directory
        archive_base = analysis_dir / ".archive"
        archive_base.mkdir(exist_ok=True)
        old_files_dir = archive_base / "migrated_old_files"
        old_files_dir.mkdir(exist_ok=True)

        # Pattern for timestamped files
        timestamp_pattern = re.compile(r".*_\d{8}_\d{6}\.(md|json)$")

        # Move all timestamped files to archive
        for file in analysis_dir.iterdir():
            if file.is_file() and timestamp_pattern.match(file.name):
                _ = shutil.move(str(file), str(old_files_dir / file.name))

        # Handle symlinks - convert to real files
        for symlink in [
            "analysis.md",
            "reviewer_feedback.json",
            "iteration_history.json",
        ]:
            link_path = analysis_dir / symlink
            if link_path.is_symlink():
                # Read the target content
                target = link_path.resolve()
                if target.exists():
                    # Remove symlink
                    link_path.unlink()
                    # Write as real file based on file type
                    if target.suffix == ".md":
                        text_content = target.read_text()
                        _ = link_path.write_text(text_content)
                    else:
                        bytes_content = target.read_bytes()
                        _ = link_path.write_bytes(bytes_content)
                else:
                    # Broken symlink, just remove it
                    link_path.unlink()

        # Check if old_files_dir has any files (for logging/debugging purposes)
        _ = len(list(old_files_dir.iterdir())) if old_files_dir.exists() else 0

    def _get_next_run_number(self, archive_base: Path, run_type: str) -> int:
        """
        Get the next run number for this type.

        Args:
            archive_base: Base archive directory
            run_type: Type of run

        Returns:
            Next run number
        """
        if not archive_base.exists():
            return 1

        pattern = re.compile(f"{run_type}_(\\d{{3}})_.*")
        max_number = 0

        for archive_dir in archive_base.iterdir():
            if archive_dir.is_dir():
                match = pattern.match(archive_dir.name)
                if match:
                    max_number = max(max_number, int(match.group(1)))

        return max_number + 1

    def _cleanup_old_archives(self, archive_base: Path):
        """
        Remove old archives beyond the maximum limit.

        Args:
            archive_base: Base archive directory
        """
        if not archive_base.exists():
            return

        # Get all archive directories with their metadata
        archives: list[tuple[Path, ArchiveMetadata]] = []
        for archive_dir in archive_base.iterdir():
            if archive_dir.is_dir() and archive_dir.name != "migrated_old_files":
                metadata_file = archive_dir / "archive_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata: ArchiveMetadata = json.load(f)
                        archives.append((archive_dir, metadata))

        # Sort by archived_at timestamp
        archives.sort(key=lambda x: x[1].get("archived_at", ""), reverse=True)

        # Keep separate limits for test and production
        test_count = 0
        prod_count = 0

        for archive_dir, metadata in archives:
            run_type = metadata.get("run_type", "production")

            if run_type == "test":
                test_count += 1
                if test_count > self.max_archives:
                    shutil.rmtree(archive_dir)
                    print(f"🗑️  Removed old test archive: {archive_dir.name}")
            else:
                prod_count += 1
                if prod_count > self.max_archives:
                    shutil.rmtree(archive_dir)
                    print(f"🗑️  Removed old archive: {archive_dir.name}")

    def create_metadata(
        self,
        analysis_result: dict[str, object],
        reviewer_feedback: dict[str, object] | None = None,
        iteration_history: list[dict[str, object]] | None = None,
    ) -> ArchiveMetadata:
        """
        Create consolidated metadata for the current run.

        Args:
            analysis_result: Result from the analysis
            reviewer_feedback: Final reviewer feedback
            iteration_history: History of iterations

        Returns:
            Consolidated metadata dictionary
        """
        word_count_val = analysis_result.get("word_count", 0)
        char_count_val = analysis_result.get("character_count", 0)

        metadata: ArchiveMetadata = {
            "created_at": datetime.now().isoformat(),
            "final_status": str(analysis_result.get("final_status", "completed")),
            "iteration_count": len(iteration_history) if iteration_history else 1,
            "word_count": int(word_count_val)
            if isinstance(word_count_val, (int, str, float))
            else 0,
            "character_count": int(char_count_val)
            if isinstance(char_count_val, (int, str, float))
            else 0,
        }

        if reviewer_feedback:
            decision = reviewer_feedback.get("decision", "N/A")
            metadata["reviewer_decision"] = str(decision)
            critical_issues = reviewer_feedback.get("critical_issues", [])
            metadata["critical_issues"] = (
                len(critical_issues) if isinstance(critical_issues, list) else 0
            )
            improvements = reviewer_feedback.get("improvements", [])
            metadata["improvements"] = (
                len(improvements) if isinstance(improvements, list) else 0
            )
            assessment = reviewer_feedback.get("assessment", "")
            metadata["assessment"] = str(assessment)

        if iteration_history:
            metadata["iterations"] = [
                {
                    "iteration": item.get("iteration", 0),
                    "timestamp": item.get("timestamp", ""),
                    "accepted": item.get("accepted", False),
                    "reason": item.get("reason", ""),
                }
                for item in iteration_history
            ]

        return metadata

    def get_archive_summary(self, analysis_dir: Path) -> ArchiveSummary:
        """
        Get a summary of archived runs.

        Args:
            analysis_dir: Directory to check

        Returns:
            Summary of archived runs
        """
        archive_base = analysis_dir / ".archive"
        if not archive_base.exists():
            return ArchiveSummary(archives=[], total=0, test_runs=0, production_runs=0)

        archives: list[ArchiveSummaryItem] = []
        for archive_dir in sorted(archive_base.iterdir()):
            if archive_dir.is_dir() and archive_dir.name != "migrated_old_files":
                metadata_file = archive_dir / "archive_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        archives.append(
                            ArchiveSummaryItem(
                                name=archive_dir.name,
                                run_type=str(metadata.get("run_type", "unknown")),
                                archived_at=str(metadata.get("archived_at", "unknown")),
                                run_number=int(metadata.get("run_number", 0)),
                            )
                        )

        return ArchiveSummary(
            archives=archives,
            total=len(archives),
            test_runs=len([a for a in archives if a["run_type"] == "test"]),
            production_runs=len([a for a in archives if a["run_type"] == "production"]),
        )
