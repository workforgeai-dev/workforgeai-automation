# WorkForgeAI Automation Engine

AI-powered content automation for [WorkForgeAI.com](https://workforgeai.com).

## Architecture

```
User -> orchestrator.py -> NEXUS API -> Ollama -> WordPress / Shop
                   |
            Raspberry Pi worker
         (cron-driven scheduling)
```

## Modes

| Mode | Description |
|------|-------------|
| `--mode=blog` | Generate + publish articles with social cross-posting |
| `--mode=products` | Create digital product bundles |
| `--mode=health` | Check NEXUS API + WordPress connectivity |
| `--mode=all` | Run blog + products in sequence |

## Pipeline

1. NEXUS API generates content via local Ollama models
2. Article published to WordPress via REST API
3. Social posts auto-crossposted
4. Digital products created in WooCommerce

## Infrastructure

- **NEXUS Server** (UM790 Pro): AI inference, API orchestration
- **Raspberry Pi**: Scheduled execution
- **Models**: nexus-omni, fully local

## Quick Start

```bash
cp .env.template .env
# Edit .env with your config
python3 orchestrator.py --mode=health
python3 orchestrator.py --mode=blog
```
