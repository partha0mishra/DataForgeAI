# Contributing to Agentic Data Pipeline Generator

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/agentic-data-pipeline.git
cd agentic-data-pipeline
```

2. **Create a virtual environment**

```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

4. **Set up pre-commit hooks**

```bash
pre-commit install
```

5. **Configure environment**

```bash
cp .env.example .env
# Add your test API keys
```

## 🎯 How to Contribute

### Adding a New LLM Provider

1. **Create a new client class** in `src/agentic_data_pipeline/core.py`:

```python
class NewLLMClient(LLMClient):
    """New LLM provider client."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize your client

    def generate(self, prompt: str) -> str:
        # Implementation
        pass

    def test_connection(self) -> TestConnectionResponse:
        # Implementation
        pass
```

2. **Add provider to enum** in `src/agentic_data_pipeline/models.py`:

```python
class LLMProvider(str, Enum):
    # ...
    NEW_PROVIDER = "new_provider"
```

3. **Update configuration**:
   - Add to `.env.example`
   - Add to `config.yaml`
   - Update `src/agentic_data_pipeline/config.py`

4. **Add tests** in `tests/test_llm_providers.py`

5. **Update documentation** in README.md

### Adding a New Platform/Orchestrator

1. **Add to enums** in `src/agentic_data_pipeline/models.py`:

```python
class Platform(str, Enum):
    # ...
    NEW_PLATFORM = "new_platform"

class Orchestrator(str, Enum):
    # ...
    NEW_ORCHESTRATOR = "new_orchestrator"
```

2. **Update system prompt** in `prompts/system_prompt.txt`:
   - Add platform-specific best practices
   - Add cost estimation formulas

3. **Add pricing** to `config.yaml`:

```yaml
generation:
  cost_estimates:
    new_platform_per_unit: 1.50
```

4. **Create example pipeline** in `examples/new_platform_example/`:
   - README.md
   - Sample generated code
   - Tests

### Adding Example Pipelines

1. **Create example directory**:

```bash
mkdir -p examples/my_example/{generated_code,tests,sample_data}
```

2. **Write comprehensive README.md**:
   - Overview and use case
   - Architecture diagram (ASCII art is fine)
   - Tech stack
   - Cost estimates
   - Quick start guide
   - Troubleshooting

3. **Add to few-shot examples** (optional):

If your example is particularly good, add it to `prompts/few_shot_examples.json`:

```json
{
  "id": 3,
  "prompt": "Your example prompt",
  "response": {
    "pipeline_name": "...",
    // ... full PipelineOutput
  }
}
```

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=agentic_data_pipeline

# Specific test file
pytest tests/test_core.py

# Specific test
pytest tests/test_core.py::test_xai_client
```

### Writing Tests

- Use `pytest` for all tests
- Mock LLM calls for unit tests
- Create integration tests for end-to-end flows
- Aim for >80% code coverage

Example:

```python
def test_new_llm_client(mocker):
    """Test new LLM client."""
    # Mock the API call
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock(message=mocker.Mock(content="test"))]

    mocker.patch("openai.OpenAI.chat.completions.create", return_value=mock_response)

    client = NewLLMClient({"api_key": "test"})
    result = client.generate("test prompt")

    assert result == "test"
```

## 📝 Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

### Format your code

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Style Guidelines

- Use type hints everywhere
- Write docstrings for all public functions (Google style)
- Keep functions under 50 lines when possible
- Use meaningful variable names
- Add comments for complex logic

Example:

```python
def process_pipeline(
    prompt: str,
    config: PipelineConfig,
    enable_rag: bool = True,
) -> PipelineOutput:
    """Process a pipeline generation request.

    Args:
        prompt: User's natural language prompt
        config: LLM configuration
        enable_rag: Whether to use RAG for context

    Returns:
        Generated pipeline output

    Raises:
        ValueError: If prompt is empty
        LLMError: If LLM generation fails
    """
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    # Implementation...
```

## 🔄 Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bugfix
```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run quality checks**

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type check
mypy src/

# Test
pytest --cov=agentic_data_pipeline
```

4. **Commit your changes**

```bash
git add .
git commit -m "feat: add support for new LLM provider"
```

Use conventional commit messages:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance

5. **Push and create PR**

```bash
git push origin feature/my-feature
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots (if UI changes)
- Test results

6. **Code Review**
   - Address review comments
   - Keep the conversation respectful
   - Be open to feedback

## 🐛 Reporting Bugs

Use GitHub Issues with the bug template:

**Title**: Clear, concise description

**Description**:
- What happened?
- What did you expect?
- Steps to reproduce
- Environment (OS, Python version, etc.)
- Logs or error messages

**Labels**: Apply relevant labels (bug, enhancement, etc.)

## 💡 Feature Requests

We love new ideas! Submit a feature request with:

1. **Use Case**: Why is this needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other solutions you considered
4. **Additional Context**: Screenshots, examples, etc.

## 📚 Documentation

Good documentation is crucial:

- Update README.md for user-facing changes
- Update docstrings for API changes
- Add examples for new features
- Update `docs/` for complex features

## 🙏 Recognition

All contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

## 📜 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## ❓ Questions?

- Open a Discussion on GitHub
- Email: support@dataforgeai.com
- Check existing issues and PRs

---

Thank you for contributing to Agentic Data Pipeline Generator! 🚀
