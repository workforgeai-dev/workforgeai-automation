#!/bin/bash
# Install all cron jobs for WorkForgeAI Automation
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORCHESTRATOR="$SCRIPT_DIR/orchestrator.py"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

cat > /tmp/workforgeai-crons << CRON
# WorkForgeAI Automation Engine - installed $(date)
# Blog posts: 3x daily
0 8,14,20 * * * cd $SCRIPT_DIR && python3 orchestrator.py --mode=blog --count=1 >> $LOG_DIR/cron.log 2>&1
# Social media: 3x daily (1h after blog)
0 9,15,21 * * * cd $SCRIPT_DIR && python3 orchestrator.py --mode=social >> $LOG_DIR/cron.log 2>&1
# Health check: every 30min
*/30 * * * * cd $SCRIPT_DIR && python3 orchestrator.py --mode=health >> $LOG_DIR/cron.log 2>&1
# Products update: weekly on Monday
0 5 * * 1 cd $SCRIPT_DIR && python3 orchestrator.py --mode=products >> $LOG_DIR/cron.log 2>&1
# Backup: daily at 3am
0 3 * * * cd $SCRIPT_DIR && python3 orchestrator.py --mode=backup >> $LOG_DIR/cron.log 2>&1
# Weekly report: Saturday noon
0 12 * * 6 cd $SCRIPT_DIR && python3 orchestrator.py --mode=report >> $LOG_DIR/cron.log 2>&1
CRON

crontab /tmp/workforgeai-crons
rm /tmp/workforgeai-crons

echo "Cron jobs installed:"
crontab -l | grep -v "^#" | grep -v "^$"
