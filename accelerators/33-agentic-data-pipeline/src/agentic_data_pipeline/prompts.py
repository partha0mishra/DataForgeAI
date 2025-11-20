"""
Prompt management for LLM interactions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """Manage system prompts and few-shot examples."""

    def __init__(
        self,
        system_prompt_path: str = "prompts/system_prompt.txt",
        few_shot_examples_path: str = "prompts/few_shot_examples.json",
    ):
        self.system_prompt_path = Path(system_prompt_path)
        self.few_shot_examples_path = Path(few_shot_examples_path)
        self._system_prompt: Optional[str] = None
        self._few_shot_examples: List[Dict] = []

        self.load_prompts()

    def load_prompts(self) -> None:
        """Load system prompt and few-shot examples from files."""
        # Load system prompt
        if self.system_prompt_path.exists():
            with open(self.system_prompt_path) as f:
                self._system_prompt = f.read()
                logger.info(f"Loaded system prompt from {self.system_prompt_path}")
        else:
            logger.warning(f"System prompt file not found: {self.system_prompt_path}")
            self._system_prompt = self._get_default_system_prompt()

        # Load few-shot examples
        if self.few_shot_examples_path.exists():
            with open(self.few_shot_examples_path) as f:
                self._few_shot_examples = json.load(f)
                logger.info(
                    f"Loaded {len(self._few_shot_examples)} few-shot examples from {self.few_shot_examples_path}"
                )
        else:
            logger.warning(f"Few-shot examples file not found: {self.few_shot_examples_path}")
            self._few_shot_examples = []

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt if file is not found."""
        return """You are an expert data engineering architect. Generate production-ready data pipeline code from natural language descriptions.

Return ONLY valid JSON in this exact schema (no additional text):

{
  "pipeline_name": "str",
  "platform": "databricks|snowflake|bigquery|synapse|redshift|aws_glue|fabric",
  "orchestrator": "airflow|delta_live_tables|dbt|mage|prefect|snowpark|synapse_pipeline",
  "description": "str",
  "estimated_monthly_cost_usd": float,
  "estimated_execution_time_minutes": float,
  "files": [{"path": "str", "content": "str"}],
  "dependencies": ["list of pip install commands"],
  "setup_instructions": "markdown string",
  "architecture_notes": "str",
  "security_considerations": "str"
}

Generate complete, production-ready code with error handling, logging, security best practices, and data quality checks.
"""

    def build_prompt(
        self, user_prompt: str, include_few_shot: bool = True, max_examples: int = 3
    ) -> str:
        """Build the full prompt including system instructions and few-shot examples.

        Args:
            user_prompt: The user's natural language request
            include_few_shot: Whether to include few-shot examples
            max_examples: Maximum number of few-shot examples to include

        Returns:
            The complete prompt to send to the LLM
        """
        parts = []

        # Add system prompt
        if self._system_prompt:
            parts.append(self._system_prompt)
            parts.append("\n---\n")

        # Add few-shot examples
        if include_few_shot and self._few_shot_examples:
            parts.append("# Example Generations\n\n")
            parts.append(
                "Here are examples of high-quality pipeline generations. Match this level of completeness and quality:\n\n"
            )

            # Select examples (for now, take first max_examples)
            examples_to_include = self._few_shot_examples[:max_examples]

            for i, example in enumerate(examples_to_include, 1):
                parts.append(f"## Example {i}\n\n")
                parts.append(f"**User Prompt:**\n{example['prompt']}\n\n")
                parts.append(f"**Generated Output:**\n```json\n{json.dumps(example['response'], indent=2)}\n```\n\n")

            parts.append("---\n\n")

        # Add user prompt
        parts.append("# User Request\n\n")
        parts.append(user_prompt)
        parts.append("\n\n# Your Response\n\n")
        parts.append(
            "Generate the complete pipeline following the examples above. Return ONLY the JSON object (no explanatory text):\n"
        )

        return "".join(parts)

    @property
    def system_prompt(self) -> str:
        """Get the system prompt."""
        return self._system_prompt or self._get_default_system_prompt()

    @property
    def few_shot_examples(self) -> List[Dict]:
        """Get the few-shot examples."""
        return self._few_shot_examples

    def get_example_prompts(self) -> List[str]:
        """Get list of example user prompts for the UI."""
        return [example["prompt"] for example in self._few_shot_examples]
