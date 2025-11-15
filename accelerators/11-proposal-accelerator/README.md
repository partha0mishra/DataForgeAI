# Accelerator 11: Proposal Accelerator

AI-powered proposal generation with templates, cost estimation, and timeline planning.

## Features

- **Template Management**: Pre-built proposal templates
- **AI-Powered Generation**: LLM-based proposal writing
- **Cost Estimation**: Automatic project cost estimation
- **Timeline Planning**: Duration estimation
- **Multiple Proposal Types**: Software, consulting, analytics, infrastructure

## Quick Start

```bash
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'
python examples/proposal_example.py
```

## API

```bash
uvicorn src.api.main:app --port 8011
```

Visit http://localhost:8011/docs

## Endpoints

- `GET /templates` - List proposal templates
- `POST /proposals/generate` - Generate proposal

## License

MIT License
