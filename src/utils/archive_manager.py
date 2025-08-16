"""Archive manager for organizing and cleaning up analysis files."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re


class ArchiveManager:
    """Manages archiving and cleanup of analysis files."""
    
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
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
            "iteration_history.json"
        ]
        
        for filename in files_to_archive:
            source = analysis_dir / filename
            if source.exists() and not source.is_symlink():
                shutil.move(str(source), str(archive_dir / filename))
        
        # Archive iteration files
        iterations_dir = analysis_dir / "iterations"
        if iterations_dir.exists():
            shutil.move(str(iterations_dir), str(archive_dir / "iterations"))
        
        # Save archive metadata
        archive_metadata = {
            "archived_at": datetime.now().isoformat(),
            "run_type": run_type,
            "run_number": run_number,
            **(metadata or {})
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
        import sys
        
        # Create archive directory
        archive_base = analysis_dir / ".archive"
        archive_base.mkdir(exist_ok=True)
        old_files_dir = archive_base / "migrated_old_files"
        old_files_dir.mkdir(exist_ok=True)
        
        # Pattern for timestamped files
        timestamp_pattern = re.compile(r'.*_\d{8}_\d{6}\.(md|json)$')
        
        # Move all timestamped files to archive
        for file in analysis_dir.iterdir():
            if file.is_file() and timestamp_pattern.match(file.name):
                shutil.move(str(file), str(old_files_dir / file.name))
        
        # Handle symlinks - convert to real files
        for symlink in ["analysis.md", "reviewer_feedback.json", "iteration_history.json"]:
            link_path = analysis_dir / symlink
            if link_path.is_symlink():
                # Read the target content
                target = link_path.resolve()
                if target.exists():
                    content = target.read_text() if target.suffix == ".md" else target.read_bytes()
                    # Remove symlink
                    link_path.unlink()
                    # Write as real file
                    if target.suffix == ".md":
                        link_path.write_text(content)
                    else:
                        link_path.write_bytes(content)
                else:
                    # Broken symlink, just remove it
                    link_path.unlink()
        
        file_count = len(list(old_files_dir.iterdir())) if old_files_dir.exists() else 0
    
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
        archives = []
        for archive_dir in archive_base.iterdir():
            if archive_dir.is_dir() and archive_dir.name != "migrated_old_files":
                metadata_file = archive_dir / "archive_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
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
        analysis_result: Dict[str, Any],
        reviewer_feedback: Optional[Dict[str, Any]] = None,
        iteration_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create consolidated metadata for the current run.
        
        Args:
            analysis_result: Result from the analysis
            reviewer_feedback: Final reviewer feedback
            iteration_history: History of iterations
            
        Returns:
            Consolidated metadata dictionary
        """
        metadata = {
            "created_at": datetime.now().isoformat(),
            "final_status": analysis_result.get("final_status", "completed"),
            "iteration_count": len(iteration_history) if iteration_history else 1,
            "word_count": analysis_result.get("word_count", 0),
            "character_count": analysis_result.get("character_count", 0),
        }
        
        if reviewer_feedback:
            metadata["reviewer_decision"] = reviewer_feedback.get("decision", "N/A")
            metadata["critical_issues"] = len(reviewer_feedback.get("critical_issues", []))
            metadata["improvements"] = len(reviewer_feedback.get("improvements", []))
            metadata["assessment"] = reviewer_feedback.get("assessment", "")
        
        if iteration_history:
            metadata["iterations"] = [
                {
                    "iteration": item.get("iteration", 0),
                    "timestamp": item.get("timestamp", ""),
                    "accepted": item.get("accepted", False),
                    "reason": item.get("reason", "")
                }
                for item in iteration_history
            ]
        
        return metadata
    
    def get_archive_summary(self, analysis_dir: Path) -> Dict[str, Any]:
        """
        Get a summary of archived runs.
        
        Args:
            analysis_dir: Directory to check
            
        Returns:
            Summary of archived runs
        """
        archive_base = analysis_dir / ".archive"
        if not archive_base.exists():
            return {"archives": [], "total": 0}
        
        archives = []
        for archive_dir in sorted(archive_base.iterdir()):
            if archive_dir.is_dir() and archive_dir.name != "migrated_old_files":
                metadata_file = archive_dir / "archive_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        archives.append({
                            "name": archive_dir.name,
                            "run_type": metadata.get("run_type", "unknown"),
                            "archived_at": metadata.get("archived_at", "unknown"),
                            "run_number": metadata.get("run_number", 0)
                        })
        
        return {
            "archives": archives,
            "total": len(archives),
            "test_runs": len([a for a in archives if a["run_type"] == "test"]),
            "production_runs": len([a for a in archives if a["run_type"] == "production"])
        }