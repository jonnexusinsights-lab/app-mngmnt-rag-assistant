import os
import yaml
from pathlib import Path
from src.core.config import settings

class PromptManager:
    def __init__(self):
        self.prompt_dir = Path(settings.PROMPT_DIR)

    def load_prompt(self, domain: str, prompt_name: str) -> str:
        """
        Load a prompt from a YAML file.
        Path: src/prompts/{domain}/{prompt_name}.yaml
        """
        try:
            prompt_path = self.prompt_dir / domain / f"{prompt_name}.yaml"

            if not prompt_path.exists():
                # Fallback to defaults or raise specific error
                # For now, return a generic string or raise
                print(f"Warning: Prompt file not found at {prompt_path}")
                return "You are a helpful AI assistant."

            with open(prompt_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Assuming simple YAML structure: { "template": "..." } or similar
            # If it's just the text, we return it.
            # Adjust based on actual YAML format.
            if isinstance(data, dict):
                return data.get("template", str(data))
            return str(data)

        except Exception as e:
            print(f"Error loading prompt {domain}/{prompt_name}: {e}")
            return "You are a helpful AI assistant."

prompt_manager = PromptManager()
