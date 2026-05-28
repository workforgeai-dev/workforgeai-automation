#!/bin/bash
# WorkForgeAI Automation - Test all connections
echo "=== Testing All Connections ==="
echo ""

echo "1. NEXUS API Health:"
python3 -c "
import httpx
try:
    r = httpx.get('http://localhost:8000/health', timeout=10)
    print(f'   Status: {r.status_code} - {r.json()}')
except Exception as e:
    print(f'   FAIL: {e}')
"

echo ""
echo "2. WordPress API:"
if [ -f .env ]; then
    source .env 2>/dev/null || true
fi
echo "   (requires WP credentials in .env or --wp-user/--wp-pass)"

echo ""
echo "3. Pi connectivity:"
ping -c 1 192.168.1.123 -W 2 >/dev/null 2>&1 && echo "   Pi: REACHABLE" || echo "   Pi: UNREACHABLE"

echo ""
echo "4. Python dependencies:"
python3 -c "
import yaml, httpx, dotenv, cryptography, apscheduler
print('   All modules: OK')
" 2>&1 || echo "   Some modules missing - run: pip3 install -r requirements.txt"

echo ""
echo "=== Test complete ==="
