#!/bin/bash
set -e
echo "=== Bootstrapping Raspberry Pi for Automation ==="

# Update system
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# Install Python dependencies
pip3 install httpx pyyaml python-dotenv cryptography apscheduler Pillow --break-system-packages 2>/dev/null || \
pip3 install httpx pyyaml python-dotenv cryptography apscheduler Pillow

# Create project directory
mkdir -p /home/erico/automation/{modules,products,scripts,logs,templates}

# Copy files from NEXUS
rsync -avz erico@192.168.1.116:/opt/godbot/automation/ /home/erico/automation/ --exclude=.env --exclude=__pycache__

# Make scripts executable
chmod +x /home/erico/automation/*.sh /home/erico/automation/scripts/*.sh 2>/dev/null || true

# Set up cron
cat > /tmp/automation-crons << 'CRON'
# WorkForgeAI Automation Engine
0 8,14,20 * * * cd /home/erico/automation && python3 orchestrator.py --mode=blog --count=1 >> logs/cron.log 2>&1
0 9,15,21 * * * cd /home/erico/automation && python3 orchestrator.py --mode=social >> logs/cron.log 2>&1
*/30 * * * * cd /home/erico/automation && python3 orchestrator.py --mode=health >> logs/cron.log 2>&1
0 5 * * 1 cd /home/erico/automation && python3 orchestrator.py --mode=products >> logs/cron.log 2>&1
0 3 * * * cd /home/erico/automation && python3 orchestrator.py --mode=backup >> logs/cron.log 2>&1
0 12 * * 6 cd /home/erico/automation && python3 orchestrator.py --mode=report >> logs/cron.log 2>&1
CRON
crontab /tmp/automation-crons 2>/dev/null || echo "[!] Could not install crontab - install manually"
rm /tmp/automation-crons

echo ""
echo "=== Pi bootstrap complete ==="
echo "Automation engine installed at /home/erico/automation"
echo "Active crons:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "(none)"
