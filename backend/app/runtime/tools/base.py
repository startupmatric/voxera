from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


@dataclass
class ToolDef:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]

    def schema(self) -> dict:
        """OpenAI-compatible tool schema for Ollama."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }
