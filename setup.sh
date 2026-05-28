#!/bin/bash
set -e
echo "=== WorkForgeAI Automation Engine - Setup ==="

# Check Python
command -v python3 >/dev/null 2>&1 || { echo "Python3 is required"; exit 1; }

# Create directories
mkdir -p modules products scripts logs templates

# Install dependencies
pip3 install -r requirements.txt 2>/dev/null || pip install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x *.sh 2>/dev/null || true

# Create .env if not exists
if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        cp .env.template .env
        echo "[!] Created .env from template - please fill in your credentials"
    else
        echo "# WorkForgeAI Automation" > .env
        echo "[!] Created empty .env"
    fi
fi

# Test connections
python3 orchestrator.py --mode=health 2>/dev/null || echo "[!] Health check will work after .env config"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: python3 scripts/test_all.py"
echo "  3. Setup cron: crontab scripts/crons.sh"
