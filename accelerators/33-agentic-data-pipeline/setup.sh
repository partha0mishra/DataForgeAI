#!/bin/bash

# Agentic Data Pipeline Generator - Quick Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "🚀 Agentic Data Pipeline Generator - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "✅ Python $PYTHON_VERSION detected"
else
    echo "❌ Python 3.10+ required. You have $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -e .

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/chroma logs output
echo "✅ Directories created"

# Copy .env.example to .env
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env and add your API keys"
else
    echo "✅ .env file already exists"
fi

# Prompt for LLM provider
echo ""
echo "Which LLM provider would you like to use?"
echo "1) xAI / Grok (recommended for code quality)"
echo "2) Azure OpenAI"
echo "3) AWS Bedrock"
echo "4) Local LLM (LM Studio)"
read -p "Select (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Selected: xAI / Grok"
        echo "Please get your API key from: https://console.x.ai/"
        read -p "Enter your xAI API key (or press Enter to skip): " api_key
        if [ ! -z "$api_key" ]; then
            sed -i.bak "s/XAI_API_KEY=.*/XAI_API_KEY=$api_key/" .env
            sed -i.bak "s/LLM_PROVIDER=.*/LLM_PROVIDER=xai/" .env
            rm .env.bak 2>/dev/null || true
            echo "✅ API key saved to .env"
        fi
        ;;
    2)
        echo ""
        echo "Selected: Azure OpenAI"
        echo "You'll need:"
        echo "  - API Key"
        echo "  - Endpoint URL"
        echo "  - Deployment name"
        echo ""
        echo "Please edit .env manually with your Azure OpenAI credentials"
        sed -i.bak "s/LLM_PROVIDER=.*/LLM_PROVIDER=azure_openai/" .env
        rm .env.bak 2>/dev/null || true
        ;;
    3)
        echo ""
        echo "Selected: AWS Bedrock"
        echo "Make sure you have AWS credentials configured"
        sed -i.bak "s/LLM_PROVIDER=.*/LLM_PROVIDER=aws_bedrock/" .env
        rm .env.bak 2>/dev/null || true
        ;;
    4)
        echo ""
        echo "Selected: Local LLM"
        echo "Make sure LM Studio (or compatible server) is running on http://localhost:1234"
        sed -i.bak "s/LLM_PROVIDER=.*/LLM_PROVIDER=local/" .env
        rm .env.bak 2>/dev/null || true
        ;;
    *)
        echo "Invalid choice. Please edit .env manually."
        ;;
esac

# Test installation
echo ""
echo "Testing installation..."
if python -c "import agentic_data_pipeline; print('✅ Package import successful')" 2>/dev/null; then
    echo "✅ Installation successful!"
else
    echo "❌ Installation test failed"
    exit 1
fi

# Print next steps
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your API key (if not done already):"
echo "   nano .env"
echo ""
echo "2. Test LLM connection:"
echo "   source venv/bin/activate"
echo "   agentic-pipeline test-llm"
echo ""
echo "3. Start the Streamlit UI:"
echo "   make ui"
echo "   # Or: streamlit run src/agentic_data_pipeline/ui.py"
echo ""
echo "4. Or use the CLI:"
echo "   agentic-pipeline generate --prompt 'Your pipeline description'"
echo ""
echo "5. Or start the API:"
echo "   make api"
echo "   # Then visit: http://localhost:8000/docs"
echo ""
echo "📚 Documentation: README.md"
echo "💬 Issues: https://github.com/your-org/agentic-data-pipeline/issues"
echo ""
echo "Happy pipeline building! 🎉"
