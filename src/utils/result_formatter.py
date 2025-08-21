"""Utility for formatting pipeline results for CLI display."""

from src.core.results import PipelineResult


def format_pipeline_result(result: PipelineResult, with_review: bool) -> None:
    """
    Format and print pipeline result to console.

    Args:
        result: Pipeline result dictionary
        with_review: Whether review mode was enabled
    """
    if not result["success"]:
        print(f"\n❌ Analysis failed: {result['message'] or 'Unknown error'}")
        return

    # Get the actual fields from pipeline result
    iterations = result["iterations"]
    analysis_file = result["analysis_path"]
    feedback_file = result["feedback_path"]

    if with_review:
        # Review mode - show iteration info
        print(f"\n✅ Analysis completed after {iterations} iteration(s)")
        if analysis_file:
            print(f"   Analysis: {analysis_file}")
        if feedback_file:
            print(f"   Feedback: {feedback_file}")
    else:
        # Simple mode - just show basic info
        if analysis_file:
            print(f"\n✅ Analysis saved to: {analysis_file}")
        else:
            print("\n✅ Analysis completed")
