"""
Utility functions for the pipeline generator.
"""

import io
import zipfile
from pathlib import Path
from typing import List, Tuple


def create_zip_file(files: List[Tuple[str, str]]) -> io.BytesIO:
    """Create a ZIP file in memory from a list of files.

    Args:
        files: List of tuples (file_path, file_content)

    Returns:
        BytesIO object containing the ZIP file
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path, content in files:
            zip_file.writestr(file_path, content)

    zip_buffer.seek(0)
    return zip_buffer


def save_pipeline_to_disk(pipeline_name: str, files: List[Tuple[str, str]], output_dir: str = "./output") -> str:
    """Save generated pipeline files to disk.

    Args:
        pipeline_name: Name of the pipeline
        files: List of tuples (file_path, file_content)
        output_dir: Output directory

    Returns:
        Path to the created directory
    """
    output_path = Path(output_dir) / pipeline_name
    output_path.mkdir(parents=True, exist_ok=True)

    for file_path, content in files:
        full_path = output_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "w") as f:
            f.write(content)

    return str(output_path)


def estimate_tokens(text: str) -> int:
    """Rough estimation of tokens in text.

    Args:
        text: Input text

    Returns:
        Estimated number of tokens
    """
    # Rough estimate: ~4 characters per token
    return len(text) // 4


def format_cost(cost_usd: float) -> str:
    """Format cost as USD string.

    Args:
        cost_usd: Cost in USD

    Returns:
        Formatted string
    """
    if cost_usd < 1:
        return f"${cost_usd:.2f}"
    elif cost_usd < 1000:
        return f"${cost_usd:.0f}"
    else:
        return f"${cost_usd:,.0f}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length.

    Args:
        text: Input text
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
