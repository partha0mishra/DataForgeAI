"""
Streamlit UI for the Agentic Data Pipeline Generator.
"""

import json
import logging
import time
from io import BytesIO
from typing import Dict, List, Optional

import streamlit as st
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from .config import config_loader, settings
from .core import create_generator
from .database import db_manager
from .models import LLMProvider, PipelineConfig, PipelineOutput
from .prompts import PromptManager
from .utils import create_zip_file, format_cost

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Agentic Data Pipeline Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "generated_pipeline" not in st.session_state:
        st.session_state.generated_pipeline = None
    if "generation_history" not in st.session_state:
        st.session_state.generation_history = []
    if "current_prompt" not in st.session_state:
        st.session_state.current_prompt = ""
    if "llm_config" not in st.session_state:
        st.session_state.llm_config = {}


def render_sidebar() -> Dict:
    """Render sidebar with LLM configuration.

    Returns:
        Dictionary with LLM configuration
    """
    st.sidebar.title("⚙️ Configuration")

    # Provider selection
    provider = st.sidebar.selectbox(
        "LLM Provider",
        options=[p.value for p in LLMProvider],
        index=0,
        help="Select the LLM provider to use for generation",
    )

    st.sidebar.divider()

    # Provider-specific configuration
    config = {"provider": provider}

    if provider == "xai":
        st.sidebar.subheader("xAI / Grok")
        api_key = st.sidebar.text_input(
            "API Key",
            value=settings.xai_api_key or "",
            type="password",
            help="Your xAI API key",
        )
        model = st.sidebar.text_input("Model", value=settings.xai_model, help="Model name")
        config.update({"api_key": api_key, "model": model})

    elif provider == "azure_openai":
        st.sidebar.subheader("Azure OpenAI")
        api_key = st.sidebar.text_input(
            "API Key",
            value=settings.azure_openai_api_key or "",
            type="password",
        )
        endpoint = st.sidebar.text_input(
            "Endpoint", value=settings.azure_openai_endpoint or "", help="Azure OpenAI endpoint URL"
        )
        deployment = st.sidebar.text_input(
            "Deployment",
            value=settings.azure_openai_deployment,
            help="Deployment name",
        )
        config.update({"api_key": api_key, "endpoint": endpoint, "model": deployment})

    elif provider == "aws_bedrock":
        st.sidebar.subheader("AWS Bedrock")
        model_id = st.sidebar.selectbox(
            "Model",
            options=[
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "anthropic.claude-3-opus-20240229",
                "meta.llama3-1-70b-instruct-v1:0",
                "meta.llama3-1-405b-instruct-v1:0",
            ],
            help="Bedrock model ID",
        )
        region = st.sidebar.text_input("AWS Region", value=settings.aws_region)
        config.update({"model": model_id, "region": region})

    elif provider == "local":
        st.sidebar.subheader("Local LLM")
        base_url = st.sidebar.text_input(
            "Base URL",
            value=settings.local_llm_base_url,
            help="OpenAI-compatible endpoint URL",
        )
        model = st.sidebar.text_input("Model", value=settings.local_llm_model)
        config.update({"base_url": base_url, "model": model})

    st.sidebar.divider()

    # Generation parameters
    st.sidebar.subheader("Generation Parameters")
    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1,
        help="0 = deterministic, 1 = creative",
    )
    max_tokens = st.sidebar.number_input(
        "Max Tokens",
        min_value=1000,
        max_value=32000,
        value=8000,
        step=1000,
        help="Maximum tokens to generate",
    )
    enable_few_shot = st.sidebar.checkbox(
        "Enable Few-Shot Examples", value=True, help="Include example generations in prompt"
    )

    config.update(
        {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "enable_few_shot": enable_few_shot,
        }
    )

    st.sidebar.divider()

    # Test connection button
    if st.sidebar.button("🔌 Test Connection", use_container_width=True):
        test_llm_connection(config)

    # Stats
    st.sidebar.divider()
    st.sidebar.subheader("📊 Statistics")
    try:
        stats = db_manager.get_stats()
        st.sidebar.metric("Total Generations", stats["total_generations"])
        st.sidebar.metric("Rated Generations", stats["rated_generations"])
        if stats["average_rating"]:
            st.sidebar.metric("Average Rating", f"{stats['average_rating']:.1f}/5")
    except Exception as e:
        logger.error(f"Failed to load stats: {e}")

    return config


def test_llm_connection(config: Dict) -> None:
    """Test LLM connection with current configuration.

    Args:
        config: LLM configuration
    """
    with st.spinner("Testing connection..."):
        try:
            generator = create_generator(config["provider"])
            result = generator.test_connection()

            if result.success:
                st.sidebar.success(
                    f"✅ {result.message}\n\nLatency: {result.latency_ms:.0f}ms"
                )
            else:
                st.sidebar.error(f"❌ {result.message}\n\nError: {result.error}")

        except Exception as e:
            st.sidebar.error(f"❌ Connection failed: {str(e)}")


def render_code_preview(pipeline: PipelineOutput) -> None:
    """Render code preview with syntax highlighting.

    Args:
        pipeline: Generated pipeline output
    """
    st.subheader("📄 Generated Files")

    # Create tabs for each file
    file_tabs = st.tabs([f["path"] for f in pipeline.files[:10]])  # Limit to 10 tabs

    for i, (tab, file) in enumerate(zip(file_tabs, pipeline.files[:10])):
        with tab:
            # Determine lexer based on file extension
            ext = file.path.split(".")[-1]
            lexer_map = {
                "py": "python",
                "sql": "sql",
                "yaml": "yaml",
                "yml": "yaml",
                "json": "json",
                "sh": "bash",
                "md": "markdown",
                "txt": "text",
            }
            lexer_name = lexer_map.get(ext, "text")

            try:
                lexer = get_lexer_by_name(lexer_name)
                formatter = HtmlFormatter(style="monokai", noclasses=True)
                highlighted = highlight(file.content, lexer, formatter)
                st.markdown(highlighted, unsafe_allow_html=True)
            except Exception:
                # Fallback to plain code block
                st.code(file.content, language=lexer_name)

            # Download button for individual file
            st.download_button(
                label=f"⬇️ Download {file.path}",
                data=file.content,
                file_name=file.path.split("/")[-1],
                mime="text/plain",
                key=f"download_{i}",
            )

    # Show count if more than 10 files
    if len(pipeline.files) > 10:
        st.info(f"Showing 10 of {len(pipeline.files)} files. Download ZIP to get all files.")


def create_download_zip(pipeline: PipelineOutput) -> BytesIO:
    """Create ZIP file for download.

    Args:
        pipeline: Generated pipeline output

    Returns:
        BytesIO with ZIP content
    """
    files = [(f.path, f.content) for f in pipeline.files]
    return create_zip_file(files)


def render_main_area(llm_config: Dict) -> None:
    """Render main content area.

    Args:
        llm_config: LLM configuration from sidebar
    """
    # Header
    st.markdown('<h1 class="main-header">🚀 Agentic Data Pipeline Generator</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Generate production-ready data pipelines from natural language using GenAI</p>',
        unsafe_allow_html=True,
    )

    # Example prompts
    prompt_manager = PromptManager()
    example_prompts = prompt_manager.get_example_prompts()

    if example_prompts:
        selected_example = st.selectbox(
            "📚 Or select a curated example:",
            options=["Custom prompt..."] + example_prompts,
            help="Choose a pre-built example or write your own",
        )
    else:
        selected_example = "Custom prompt..."

    # Prompt input
    if selected_example == "Custom prompt...":
        default_prompt = st.session_state.current_prompt
    else:
        default_prompt = selected_example

    user_prompt = st.text_area(
        "🎯 Describe your data pipeline:",
        value=default_prompt,
        height=150,
        placeholder="Example: Ingest daily CSV sales files from S3, apply deduplication and validation, and load into Snowflake using dbt with medallion architecture...",
        help="Describe what your pipeline should do in natural language",
    )

    st.session_state.current_prompt = user_prompt

    # Generation options
    col1, col2 = st.columns([3, 1])

    with col1:
        include_tests = st.checkbox("Include test files", value=True)
        include_docs = st.checkbox("Include documentation", value=True)

    with col2:
        generate_button = st.button("✨ Generate Pipeline", type="primary", use_container_width=True)
        refine_button = st.button(
            "🔄 Refine",
            use_container_width=True,
            disabled=st.session_state.generated_pipeline is None,
        )

    # Generate pipeline
    if generate_button and user_prompt:
        generate_pipeline(user_prompt, llm_config, include_tests, include_docs)

    # Refine pipeline
    if refine_button and user_prompt:
        refinement = st.text_input(
            "Refinement instructions:",
            placeholder="e.g., 'make it incremental' or 'add PII masking'",
        )
        if refinement:
            refined_prompt = f"{st.session_state.current_prompt}\n\nAdditional requirements: {refinement}"
            generate_pipeline(refined_prompt, llm_config, include_tests, include_docs)

    # Display results
    if st.session_state.generated_pipeline:
        display_results(st.session_state.generated_pipeline)


def generate_pipeline(
    prompt: str, llm_config: Dict, include_tests: bool, include_docs: bool
) -> None:
    """Generate a data pipeline.

    Args:
        prompt: User prompt
        llm_config: LLM configuration
        include_tests: Whether to include tests
        include_docs: Whether to include docs
    """
    with st.spinner("🤖 Generating your pipeline... This may take 30-60 seconds..."):
        start_time = time.time()

        try:
            # Create generator
            config = PipelineConfig(
                provider=LLMProvider(llm_config["provider"]),
                model=llm_config.get("model", ""),
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                enable_few_shot=llm_config["enable_few_shot"],
            )
            generator = create_generator(llm_config["provider"])

            # Generate
            pipeline = generator.generate(prompt)

            generation_time = time.time() - start_time

            # Save to database
            try:
                db_manager.save_generation(
                    prompt=prompt,
                    pipeline_output=pipeline,
                    config=llm_config,
                    generation_time_seconds=generation_time,
                )
            except Exception as e:
                logger.error(f"Failed to save to database: {e}")

            # Store in session state
            st.session_state.generated_pipeline = pipeline
            st.session_state.generation_history.append(
                {
                    "prompt": prompt,
                    "pipeline": pipeline,
                    "time": generation_time,
                }
            )

            st.success(f"✅ Pipeline generated successfully in {generation_time:.1f}s!")

        except Exception as e:
            st.error(f"❌ Generation failed: {str(e)}")
            logger.error(f"Generation error: {e}", exc_info=True)


def display_results(pipeline: PipelineOutput) -> None:
    """Display generated pipeline results.

    Args:
        pipeline: Generated pipeline
    """
    st.divider()

    # Pipeline overview
    st.subheader("📋 Pipeline Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Platform", pipeline.platform.value.title())
    with col2:
        st.metric("Orchestrator", pipeline.orchestrator.value.replace("_", " ").title())
    with col3:
        st.metric("Monthly Cost", format_cost(pipeline.estimated_monthly_cost_usd))
    with col4:
        if pipeline.estimated_execution_time_minutes:
            st.metric("Execution Time", f"{pipeline.estimated_execution_time_minutes:.0f} min")

    st.markdown(f"**Description:** {pipeline.description}")

    # Code preview
    st.divider()
    render_code_preview(pipeline)

    # Setup instructions
    st.divider()
    st.subheader("📖 Setup Instructions")
    st.markdown(pipeline.setup_instructions)

    # Architecture notes
    if pipeline.architecture_notes:
        with st.expander("🏗️ Architecture Notes"):
            st.markdown(pipeline.architecture_notes)

    # Security considerations
    if pipeline.security_considerations:
        with st.expander("🔒 Security Considerations"):
            st.markdown(pipeline.security_considerations)

    # Dependencies
    with st.expander("📦 Dependencies"):
        for dep in pipeline.dependencies:
            st.code(dep, language="bash")

    # Action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        # Download ZIP
        zip_buffer = create_download_zip(pipeline)
        st.download_button(
            label="📥 Download as ZIP",
            data=zip_buffer,
            file_name=f"{pipeline.pipeline_name}.zip",
            mime="application/zip",
            use_container_width=True,
        )

    with col2:
        # Copy to clipboard (using Streamlit's built-in)
        all_files_text = "\n\n".join([f"# {f.path}\n{f.content}" for f in pipeline.files])
        st.download_button(
            label="📋 Download All Files",
            data=all_files_text,
            file_name=f"{pipeline.pipeline_name}_all_files.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col3:
        if st.button("⭐ Rate This Generation", use_container_width=True):
            st.session_state.show_rating = True

    # Rating interface
    if st.session_state.get("show_rating", False):
        st.divider()
        st.subheader("⭐ Rate This Generation")
        rating = st.slider("How satisfied are you?", 0, 5, 3)
        feedback = st.text_area("Any feedback?", placeholder="Optional feedback...")
        if st.button("Submit Rating"):
            # In a real app, save this to database
            st.success("Thank you for your feedback!")
            st.session_state.show_rating = False


def main() -> None:
    """Main Streamlit app."""
    init_session_state()
    llm_config = render_sidebar()
    render_main_area(llm_config)


if __name__ == "__main__":
    main()
