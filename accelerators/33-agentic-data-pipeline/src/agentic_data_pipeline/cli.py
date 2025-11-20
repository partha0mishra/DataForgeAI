"""
Command-line interface for the Agentic Data Pipeline Generator.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from .config import config_loader
from .core import create_generator
from .models import LLMProvider
from .utils import save_pipeline_to_disk

app = typer.Typer(
    name="agentic-pipeline",
    help="Generate production-ready data pipelines from natural language using GenAI",
)
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors in CLI
    format="%(levelname)s: %(message)s",
)


@app.command()
def generate(
    prompt: str = typer.Option(
        ..., "--prompt", "-p", help="Natural language description of the pipeline"
    ),
    output_dir: str = typer.Option(
        "./output", "--output-dir", "-o", help="Output directory for generated files"
    ),
    provider: str = typer.Option(
        None, "--provider", help="LLM provider (xai, azure_openai, aws_bedrock, local)"
    ),
    temperature: float = typer.Option(0.0, "--temperature", "-t", help="Generation temperature (0-1)"),
    max_tokens: int = typer.Option(8000, "--max-tokens", help="Maximum tokens to generate"),
    save_json: bool = typer.Option(
        False, "--save-json", help="Also save raw JSON output"
    ),
) -> None:
    """Generate a data pipeline from a natural language prompt.

    Example:
        agentic-pipeline generate \\
            --prompt "Ingest CSV from S3 to Snowflake using dbt" \\
            --output-dir ./my_pipeline \\
            --provider xai
    """
    console.print(
        Panel.fit(
            "🚀 Agentic Data Pipeline Generator",
            subtitle="Powered by GenAI",
            border_style="blue",
        )
    )

    # Show configuration
    config_table = Table(title="Configuration", show_header=False)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Provider", provider or config_loader.get("llm.provider", "xai"))
    config_table.add_row("Temperature", str(temperature))
    config_table.add_row("Max Tokens", str(max_tokens))
    config_table.add_row("Output Dir", output_dir)

    console.print(config_table)
    console.print()

    # Generate pipeline
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating pipeline...", total=None)

        try:
            start_time = time.time()

            # Create generator
            generator = create_generator(provider)

            # Generate
            pipeline_output = generator.generate(prompt)

            generation_time = time.time() - start_time

            progress.update(task, completed=True)

            # Display success
            console.print()
            console.print(
                Panel.fit(
                    f"✅ Successfully generated pipeline: [bold]{pipeline_output.pipeline_name}[/bold]\n"
                    f"⏱️  Generation time: {generation_time:.1f}s",
                    border_style="green",
                )
            )

            # Display summary
            summary_table = Table(title="Pipeline Summary", show_header=False)
            summary_table.add_column("Property", style="cyan")
            summary_table.add_column("Value", style="white")

            summary_table.add_row("Name", pipeline_output.pipeline_name)
            summary_table.add_row("Platform", pipeline_output.platform.value)
            summary_table.add_row("Orchestrator", pipeline_output.orchestrator.value)
            summary_table.add_row("Files Generated", str(len(pipeline_output.files)))
            summary_table.add_row(
                "Est. Monthly Cost", f"${pipeline_output.estimated_monthly_cost_usd:.2f}"
            )
            if pipeline_output.estimated_execution_time_minutes:
                summary_table.add_row(
                    "Est. Execution Time",
                    f"{pipeline_output.estimated_execution_time_minutes:.0f} minutes",
                )

            console.print()
            console.print(summary_table)

            # Save files
            console.print()
            console.print("[bold]Saving files...[/bold]")

            files = [(f.path, f.content) for f in pipeline_output.files]
            output_path = save_pipeline_to_disk(
                pipeline_output.pipeline_name, files, output_dir
            )

            # Also save JSON if requested
            if save_json:
                json_path = Path(output_path) / "pipeline_output.json"
                with open(json_path, "w") as f:
                    json.dump(pipeline_output.model_dump(), f, indent=2, default=str)
                console.print(f"  💾 Saved JSON to: {json_path}")

            console.print(f"  ✅ Saved {len(files)} files to: [bold]{output_path}[/bold]")

            # Show file list
            console.print()
            console.print("[bold]Generated files:[/bold]")
            for file in pipeline_output.files[:10]:  # Show first 10
                console.print(f"  📄 {file.path}")
            if len(pipeline_output.files) > 10:
                console.print(f"  ... and {len(pipeline_output.files) - 10} more")

            console.print()
            console.print(
                Panel.fit(
                    f"🎉 Pipeline ready!\n\n"
                    f"📂 Location: {output_path}\n"
                    f"📖 See README.md or setup instructions for deployment steps",
                    border_style="green",
                )
            )

        except Exception as e:
            progress.update(task, completed=True)
            console.print()
            console.print(f"[bold red]❌ Generation failed:[/bold red] {str(e)}")
            sys.exit(1)


@app.command()
def test_llm(
    provider: str = typer.Option(
        None, "--provider", help="LLM provider to test (xai, azure_openai, aws_bedrock, local)"
    ),
) -> None:
    """Test connection to the LLM provider.

    Example:
        agentic-pipeline test-llm --provider xai
    """
    console.print(Panel.fit("🔌 Testing LLM Connection", border_style="blue"))

    provider = provider or config_loader.get("llm.provider", "xai")

    console.print(f"\nTesting connection to [bold]{provider}[/bold]...")

    try:
        generator = create_generator(provider)
        result = generator.test_connection()

        if result.success:
            console.print()
            console.print(
                Panel.fit(
                    f"✅ {result.message}\n"
                    f"⏱️  Latency: {result.latency_ms:.0f}ms\n"
                    f"🤖 Model: {result.model}",
                    border_style="green",
                )
            )
        else:
            console.print()
            console.print(
                Panel.fit(
                    f"❌ {result.message}\n\n" f"Error: {result.error}", border_style="red"
                )
            )
            sys.exit(1)

    except Exception as e:
        console.print()
        console.print(f"[bold red]❌ Connection test failed:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def list_examples() -> None:
    """List available example prompts."""
    from .prompts import PromptManager

    console.print(Panel.fit("📚 Example Prompts", border_style="blue"))

    try:
        prompt_manager = PromptManager()
        examples = prompt_manager.get_example_prompts()

        if not examples:
            console.print("\n[yellow]No examples found[/yellow]")
            return

        console.print(f"\n[bold]Found {len(examples)} example prompts:[/bold]\n")

        for i, example in enumerate(examples, 1):
            console.print(f"{i}. {example[:100]}...")
            console.print()

        console.print(
            "[dim]Use these prompts with the 'generate' command to get started quickly.[/dim]"
        )

    except Exception as e:
        console.print(f"[bold red]❌ Failed to load examples:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def interactive() -> None:
    """Run in interactive mode with prompts."""
    console.print(
        Panel.fit(
            "🚀 Agentic Data Pipeline Generator - Interactive Mode",
            subtitle="Press Ctrl+C to exit",
            border_style="blue",
        )
    )

    try:
        # Prompt for configuration
        console.print("\n[bold]Configuration:[/bold]")

        provider = typer.prompt(
            "LLM Provider (xai/azure_openai/aws_bedrock/local)",
            default=config_loader.get("llm.provider", "xai"),
        )

        temperature = typer.prompt("Temperature (0.0-1.0)", default=0.0, type=float)

        output_dir = typer.prompt("Output directory", default="./output")

        # Prompt for pipeline description
        console.print("\n[bold]Pipeline Description:[/bold]")
        console.print(
            "[dim]Describe your data pipeline in natural language (press Enter twice when done)[/dim]"
        )

        lines = []
        while True:
            line = input()
            if line:
                lines.append(line)
            else:
                break

        prompt = "\n".join(lines)

        if not prompt.strip():
            console.print("[red]No prompt provided. Exiting.[/red]")
            sys.exit(1)

        # Generate
        generate(
            prompt=prompt,
            output_dir=output_dir,
            provider=provider,
            temperature=temperature,
        )

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancelled by user[/yellow]")
        sys.exit(0)


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__

    console.print(f"Agentic Data Pipeline Generator v{__version__}")


if __name__ == "__main__":
    app()
