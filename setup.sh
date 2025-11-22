#!/bin/bash
# Setup script for Shortcuts Reverse Engineering Toolkit

echo "🚀 Setting up Shortcuts Reverse Engineering Toolkit..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create output directories
echo "📁 Creating output directories..."
mkdir -p output/actions
mkdir -p output/protobuf_decoded
mkdir -p utils

# Create __init__.py for utils
touch utils/__init__.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the main extraction script:"
echo "  python3 extract_shortcuts_actions.py"
echo ""
