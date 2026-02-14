import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class PromptManager:
    def __init__(self, prompt_dir: str = "src/prompts"):
        self.prompt_dir = Path(prompt_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, domain: str, template_name: str) -> str:
        """
        Load a prompt template from a YAML file.
        Path format: src/prompts/<domain>/<template_name>.yaml
        """
        key = f"{domain}/{template_name}"
        if key in self._cache:
            return self._cache[key]

        file_path = self.prompt_dir / domain / f"{template_name}.yaml"

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not data or "template" not in data:
                    raise ValueError(f"Invalid prompt file format: {file_path}")

                template_content = data["template"]
                self._cache[key] = template_content
                return template_content
        except Exception as e:
            raise RuntimeError(f"Error loading prompt {key}: {e}")

    def get_formatted_prompt(self, domain: str, template_name: str, **kwargs) -> str:
        """
        Load and format a prompt template with variables.
        """
        template = self.load_prompt(domain, template_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable for prompt format: {e}")

prompt_manager = PromptManager()
