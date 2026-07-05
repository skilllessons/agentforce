"""JSON Schema validation for tool inputs.

We use jsonschema-style validation indirectly: each tool typically defines a
pydantic model and exposes ``model_json_schema()`` as ``input_schema``. The
runtime validates the LLM-supplied input against the model when it's available;
otherwise it falls back to a permissive pass-through.

This keeps the contract simple: tools that want strict validation construct a
pydantic model in their ``call`` method.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError


class ValidationError(Exception):
    def __init__(self, message: str, details: list[Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


def validate_input[ModelT: BaseModel](
    input_: Any, model: type[ModelT]
) -> ModelT:
    """Coerce a raw dict into a typed pydantic model.

    Re-raises pydantic errors as a flat ValidationError so tool ``call``
    methods can return ``ToolResult(data=None, error=...)`` cleanly.
    """
    try:
        return model.model_validate(input_)
    except PydanticValidationError as e:
        raise ValidationError(
            f"Input failed schema validation: {e}",
            details=e.errors(),
        ) from e
