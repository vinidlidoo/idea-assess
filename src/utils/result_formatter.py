"""Utility for formatting pipeline results for CLI display."""

from src.core.types import PipelineResult


def format_pipeline_result(result: PipelineResult, with_review: bool) -> None:
    """
    Format and print pipeline result to console.

    Args:
        result: Pipeline result dictionary
        with_review: Whether review mode was enabled
    """
    if not result.get("success", False):
        print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
        return

    # Get the actual fields from pipeline result
    iterations = result.get("iterations_completed", 1)
    analysis_file = result.get("analysis_file", "unknown")
    final_status = result.get("final_status", "completed")

    if with_review:
        # Review mode - show detailed feedback
        if final_status == "completed":
            status_emoji = "✅"
            status_text = "COMPLETED"
        elif final_status == "max_iterations_reached":
            status_emoji = "⚠️"
            status_text = "MAX ITERATIONS REACHED"
        else:
            status_emoji = "✅"
            status_text = final_status.upper()

        print(
            f"\n{status_emoji} Analysis {status_text} after {iterations} iteration(s)"
        )
        print(f"   Saved to: {analysis_file}")

        # Note: We don't have feedback_history in the result anymore
        # This was from an older version. The pipeline now just returns
        # the final status and file paths.

    else:
        # Simple mode - just show basic info
        print(f"\n✅ Analysis saved to: {analysis_file}")
