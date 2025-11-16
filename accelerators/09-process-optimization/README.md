# Accelerator 9: Business Process Optimization

Discover, analyze, and optimize business processes using process mining and AI-powered recommendations.

## Features

- **Process Mining**: Discover process models from event logs
- **Bottleneck Detection**: Identify duration, frequency, waiting, resource, and path bottlenecks  
- **Optimization Recommendations**: AI-powered suggestions for process improvements
- **BPMN Export**: Export discovered processes as BPMN models
- **Health Scoring**: Overall process health assessment (0-100)
- **Implementation Roadmap**: Phased optimization plan with quick wins

## Quick Start

```bash
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'  # Optional, for AI recommendations
python examples/optimization_example.py
```

## API

```bash
uvicorn src.api.main:app --port 8009
```

Visit http://localhost:8009/docs

## Endpoints

- `POST /process/discover` - Discover process from event log
- `POST /process/analyze` - Analyze bottlenecks
- `POST /process/optimize` - Complete optimization analysis
- `POST /process/export/bpmn` - Export BPMN model

## License

MIT License
