import os
from typing import Any, Dict
from langfuse import Langfuse


def get_langfuse() -> Langfuse:
    """Return a Langfuse client instance created from environment configuration."""
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST"),
    )


def get_prompt_template(prompt_name: str):
    """Fetch a Langfuse prompt template by name."""
    return get_langfuse().get_prompt(prompt_name)


def compile_prompt(prompt_name: str, **kwargs: Any) -> Any:
    """Compile a Langfuse prompt template with optional keyword arguments."""
    return get_prompt_template(prompt_name).compile(**kwargs)


def preload_prompts(prompt_names: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience helper to compile multiple prompts at once.

    Args:
        prompt_names: Mapping of identifier to dict containing `name` and
            optional `kwargs` used for compilation.
    """
    compiled = {}
    for identifier, prompt_meta in prompt_names.items():
        name = prompt_meta.get("name")
        kwargs = prompt_meta.get("kwargs", {})
        if not name:
            raise ValueError(f"Prompt '{identifier}' missing required key 'name'.")
        compiled[identifier] = compile_prompt(name, **kwargs)
    return compiled

