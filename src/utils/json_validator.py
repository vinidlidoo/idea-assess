"""JSON validation using templates as source of truth."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportExplicitAny=false

import json
from pathlib import Path
from typing import Any, Literal


class JsonResponseValidator:
    """Validates agent JSON outputs against their templates."""

    schema_type: Literal["reviewer", "fact_checker"]
    template_path: Path
    template: dict[str, Any]
    required_fields: set[str]
    structure: dict[str, Any]

    def __init__(
        self,
        schema_type: Literal["reviewer", "fact_checker"] = "reviewer",
        template_dir: Path | None = None,
    ):
        """
        Initialize the validator with the appropriate template.

        Args:
            schema_type: Type of schema to use ('reviewer' or 'fact_checker')
            template_dir: Directory containing templates (defaults to config/templates)
        """
        if template_dir is None:
            # Default to project's template directory
            project_root = Path(__file__).parent.parent.parent
            template_dir = project_root / "config" / "templates"

        # Map schema type to template file
        template_files = {
            "reviewer": "agents/reviewer/feedback.json",
            "fact_checker": "agents/factchecker/fact-check.json",
        }

        if schema_type not in template_files:
            raise ValueError(f"Unknown schema type: {schema_type}")

        self.schema_type = schema_type
        self.template_path = template_dir / template_files[schema_type]

        # Load template
        with open(self.template_path, "r") as f:
            self.template = json.load(f)

        # Extract structure from template
        self.required_fields = self._extract_required_fields(self.template)
        self.structure = self._extract_structure(self.template)

    def _extract_required_fields(self, obj: Any, path: str = "") -> set[str]:
        """
        Extract fields that are required (contain TODO markers).

        Returns set of field paths like 'issues.0.claim' for nested fields.
        """
        required: set[str] = set()

        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{path}.{key}" if path else key
                if self._contains_todo(value):
                    required.add(field_path)
                # Recurse into nested structures
                if isinstance(value, (dict, list)):
                    required.update(self._extract_required_fields(value, field_path))
        elif isinstance(obj, list) and obj:
            # Check first item in list as template
            if obj and not isinstance(obj[0], str) or not self._contains_todo(obj[0]):
                required.update(self._extract_required_fields(obj[0], f"{path}.0"))

        return required

    def _extract_structure(self, obj: Any) -> Any:
        """Extract expected structure from template."""
        if isinstance(obj, dict):
            return {k: self._extract_structure(v) for k, v in obj.items()}
        elif isinstance(obj, list) and obj:
            # Use first item as template for list items
            first_item = obj[0]
            if not isinstance(first_item, str) or not self._contains_todo(first_item):
                return [self._extract_structure(first_item)]
            return []  # Simple string list
        else:
            # Infer type from template value
            return type(obj).__name__ if not self._contains_todo(obj) else "string"

    def _contains_todo(self, value: Any) -> bool:
        """Check if value contains TODO marker."""
        if value is None:
            return False
        if isinstance(value, (dict, list)):
            return False  # Only check leaf values
        return "TODO" in str(value)

    def validate(self, data: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate data against template structure.

        Args:
            data: The dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if data is valid
            - error_message: Error description if invalid, None if valid
        """
        # Check for TODO values in data
        todo_fields = self._find_todo_fields(data)
        if todo_fields:
            return False, f"Found TODO markers in fields: {', '.join(todo_fields)}"

        # Check required top-level fields exist
        for field in self.required_fields:
            # Only check top-level required fields for basic validation
            if "." not in field and field not in data:
                return False, f"Missing required field: {field}"

        # Check basic structure matches
        structure_errors = self._validate_structure(data, self.template)
        if structure_errors:
            return False, structure_errors[0]

        return True, None

    def _find_todo_fields(self, obj: Any, path: str = "") -> list[str]:
        """Find any fields that still contain TODO markers."""
        todo_fields: list[str] = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{path}.{key}" if path else key
                if self._contains_todo(value):
                    todo_fields.append(field_path)
                elif isinstance(value, (dict, list)):
                    todo_fields.extend(self._find_todo_fields(value, field_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                field_path = f"{path}.{i}"
                if self._contains_todo(item):
                    todo_fields.append(field_path)
                elif isinstance(item, (dict, list)):
                    todo_fields.extend(self._find_todo_fields(item, field_path))

        return todo_fields

    def _validate_structure(
        self, data: Any, template: Any, path: str = ""
    ) -> list[str]:
        """Validate data structure matches template."""
        errors: list[str] = []

        if isinstance(template, dict):
            if not isinstance(data, dict):
                errors.append(f"{path or 'root'} should be an object")
                return errors

            # Check expected keys exist (but don't require all template keys)
            # This is lenient - we mainly check TODO fields aren't present
            for key, template_value in template.items():
                if key in data:
                    field_path = f"{path}.{key}" if path else key
                    errors.extend(
                        self._validate_structure(data[key], template_value, field_path)
                    )

        elif isinstance(template, list) and template:
            if not isinstance(data, list):
                # Allow empty lists
                if data is not None:
                    errors.append(f"{path or 'root'} should be an array")
            elif (
                data
                and not isinstance(template[0], str)
                or not self._contains_todo(template[0])
            ):
                # Validate list items against template
                for i, item in enumerate(data):
                    errors.extend(
                        self._validate_structure(item, template[0], f"{path}.{i}")
                    )

        return errors

    def validate_file(self, file_path: Path) -> tuple[bool, str | None]:
        """
        Validate data from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return self.validate(data)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"
        except FileNotFoundError:
            return False, f"File not found: {file_path}"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    def fix_common_issues(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Attempt to fix common issues in data.

        Args:
            data: The dictionary to fix

        Returns:
            Fixed dictionary
        """
        if self.schema_type == "reviewer":
            return self._fix_reviewer_issues(data)
        elif self.schema_type == "fact_checker":
            return self._fix_fact_check_issues(data)
        return data

    def _fix_reviewer_issues(self, feedback: dict[str, Any]) -> dict[str, Any]:
        """Fix common issues in reviewer feedback."""
        # Ensure arrays exist for array fields in template
        template_arrays = {k for k, v in self.template.items() if isinstance(v, list)}
        for field in template_arrays:
            if field not in feedback:
                feedback[field] = []

        # Map legacy fields
        if "iteration_recommendation" in feedback and "recommendation" not in feedback:
            rec = feedback.get("iteration_recommendation", "").lower()
            if rec in ["accept", "approve"]:
                feedback["recommendation"] = "approve"
            elif rec == "reject":
                feedback["recommendation"] = "reject"

        # Normalize recommendation values
        if "recommendation" in feedback:
            rec = str(feedback["recommendation"]).lower()
            if rec in ["accept", "approve", "pass"]:
                feedback["recommendation"] = "approve"
            elif rec in ["reject", "fail"]:
                feedback["recommendation"] = "reject"
            elif rec == "revise":
                feedback["recommendation"] = "revise"

        # Remove any TODO placeholders
        feedback = self._remove_todos(feedback)

        return feedback

    def _fix_fact_check_issues(self, fact_check: dict[str, Any]) -> dict[str, Any]:
        """Fix common issues in fact-check results."""
        # Ensure arrays exist for array fields in template
        template_arrays = {k for k, v in self.template.items() if isinstance(v, list)}
        for field in template_arrays:
            if field not in fact_check:
                fact_check[field] = []

        # Ensure statistics exists
        if "statistics" not in fact_check:
            fact_check["statistics"] = {}

        # Map legacy fields
        if (
            "recommendation" in fact_check
            and "iteration_recommendation" not in fact_check
        ):
            fact_check["iteration_recommendation"] = fact_check.pop("recommendation")

        # Normalize recommendation values
        if "iteration_recommendation" in fact_check:
            rec = str(fact_check["iteration_recommendation"]).lower()
            if rec in ["accept", "approve", "pass"]:
                fact_check["iteration_recommendation"] = "approve"
            elif rec in ["reject", "fail", "revise"]:
                fact_check["iteration_recommendation"] = "reject"

        # Normalize severity values in issues
        if isinstance(fact_check.get("issues"), list):
            for issue in fact_check["issues"]:
                if isinstance(issue, dict) and "severity" in issue:
                    sev = str(issue["severity"]).lower()
                    if sev in ["high", "critical"]:
                        issue["severity"] = "High"
                    elif sev in ["medium", "major"]:
                        issue["severity"] = "Medium"
                    elif sev in ["low", "minor"]:
                        issue["severity"] = "Low"

        # Remove any TODO placeholders
        fact_check = self._remove_todos(fact_check)

        return fact_check

    def _remove_todos(self, obj: Any) -> Any:
        """Recursively remove TODO placeholders from data."""
        if isinstance(obj, dict):
            return {
                k: self._remove_todos(v)
                for k, v in obj.items()
                if not self._contains_todo(v)
            }
        elif isinstance(obj, list):
            return [
                self._remove_todos(item)
                for item in obj
                if not self._contains_todo(item)
            ]
        else:
            return obj if not self._contains_todo(obj) else None


# Backward compatibility alias
FeedbackValidator = JsonResponseValidator
