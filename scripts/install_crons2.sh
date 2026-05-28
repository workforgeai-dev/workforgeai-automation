#!/bin/bash
mkdir -p /home/erico/automation/logs
cat > /tmp/workforgeai-crons << CRONEOF
0 8,14,20 * * * cd /home/erico/automation && /usr/bin/python3 orchestrator.py --mode=blog --count=1 >> /home/erico/automation/logs/cron.log 2>&1
0 9,15,21 * * * cd /home/erico/automation && /usr/bin/python3 orchestrator.py --mode=social >> /home/erico/automation/logs/cron.log 2>&1
*/30 * * * * cd /home/erico/automation && /usr/bin/python3 orchestrator.py --mode=health >> /home/erico/automation/logs/cron.log 2>&1
0 5 * * 1 cd /home/erico/automation && /usr/bin/python3 orchestrator.py --mode=products >> /home/erico/automation/logs/cron.log 2>&1
0 3 * * * cd /home/erico/automation && /usr/bin/python3 orchestrator.py --mode=backup >> /home/erico/automation/logs/cron.log 2>&1
0 12 * * 6 cd /home/erico/automation && /usr/bin/python3 orchestrator.py --mode=report >> /home/erico/automation/logs/cron.log 2>&1
CRONEOF
crontab /tmp/workforgeai-crons
rm /tmp/workforgeai-crons
echo === INSTALLED ===
crontab -l | grep -v ^# | grep -v ^$
