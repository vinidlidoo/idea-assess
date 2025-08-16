"""Centralized prompt registry for managing prompt file locations."""


# Prompt file mappings after reorganization
PROMPT_REGISTRY: dict[str, str] = {
    # Active agent prompts
    "analyst_v3.md": "agents/analyst/main.md",
    "analyst_revision.md": "agents/analyst/revision.md",
    "analyst_user.md": "agents/analyst/partials/user_instruction.md",
    "analyst_resources.md": "agents/analyst/partials/resource_constraints.md",
    
    "reviewer_v1.md": "agents/reviewer/main.md",
    "reviewer_instructions.md": "agents/reviewer/instructions.md",
    
    "judge.md": "agents/judge/main.md",
    "synthesizer.md": "agents/synthesizer/main.md",
    
    # Historical versions (for reference/rollback)
    "analyst_v1.md": "versions/analyst/v1.md",
    "analyst_v2.md": "versions/analyst/v2.md",
    "reviewer_v1_simple.md": "versions/reviewer/v1_simple.md",
}


def get_prompt_path(old_name: str) -> str:
    """
    Get the new path for a prompt file based on its old name.
    
    Args:
        old_name: The old prompt file name
        
    Returns:
        The new path relative to the prompts directory
    """
    return PROMPT_REGISTRY.get(old_name, old_name)