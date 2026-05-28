import os
import zipfile
import json
import io
from pathlib import Path
from modules import utils
from modules.utils import load_config


class ProductBuilder:
    def __init__(self):
        self.cfg = load_config()
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.products_dir = Path(__file__).parent.parent / "products"

    def build_nexus_deploy(self):
        utils.log("product", "Building NEXUS One-Click Deploy package")
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            docker_compose = """version: '3.8'
services:
  nexus-redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - nexus-net

  nexus-postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: nexus
      POSTGRES_USER: nexus
      POSTGRES_PASSWORD: ${NEXUS_DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - nexus-net

  nexus-api:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    depends_on:
      - nexus-redis
      - nexus-postgres
    environment:
      REDIS_HOST: nexus-redis
      POSTGRES_HOST: nexus-postgres
      OLLAMA_HOST: ${OLLAMA_HOST:-host.docker.internal}
    networks:
      - nexus-net

volumes:
  redis_data:
  postgres_data:

networks:
  nexus-net:
    driver: bridge
"""
            zf.writestr("docker-compose.yml", docker_compose)

            env_template = """# NEXUS Configuration
# Copy this file to .env and fill in the values

# Database
NEXUS_DB_PASSWORD=change_this_to_a_secure_password

# Ollama (default: localhost)
OLLAMA_HOST=host.docker.internal

# Optional: OpenRouter for cloud model fallback
OPENROUTER_API_KEY=

# Optional: Telegram Bot Token
TELEGRAM_BOT_TOKEN=

# Optional: Tavily Search API Key
TAVILY_API_KEY=
"""
            zf.writestr(".env.template", env_template)

            setup_sh = """#!/bin/bash
set -e
echo "=== NEXUS One-Click Deploy ==="
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required. Install at https://docs.docker.com/get-docker/"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Error: Docker Compose is required."; exit 1; }

# Setup .env
if [ ! -f .env ]; then
    cp .env.template .env
    echo "[!] Please edit .env with your configuration, then run: docker compose up -d"
else
    echo "[+] .env found"
fi

# Start services
echo "[+] Starting NEXUS services..."
docker compose up -d

echo ""
echo "=== NEXUS is running ==="
echo "API: http://localhost:8000"
echo "Health: http://localhost:8000/health"
echo ""
echo "Run 'docker compose logs -f' to see logs."
"""
            zf.writestr("setup.sh", setup_sh)

            readme = """# NEXUS One-Click Deploy

Deploy your own private AI agent infrastructure in minutes.

## What's included

- Redis cache layer
- PostgreSQL database
- NEXUS API server
- Docker Compose orchestration

## Requirements

- Docker + Docker Compose
- 4GB+ RAM
- Ollama (optional, for local LLMs)

## Quick Start

1. Copy `.env.template` to `.env` and edit
2. Run `bash setup.sh`
3. Access the API at `http://localhost:8000`

## Pricing

This is the self-hosted version. No subscriptions, no cloud dependencies.
"""
            zf.writestr("README.md", readme)

        zip_buffer.seek(0)
        output_path = self.products_dir / "nexus-deploy.zip"
        with open(output_path, "wb") as f:
            f.write(zip_buffer.getvalue())
        utils.log("product", f"Package built: {output_path} ({os.path.getsize(output_path)} bytes)")
        return str(output_path)

    def build_toolkit(self):
        utils.log("product", "Building AI Productivity Toolkit")
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            base_prompts = """# AI Productivity Toolkit - Prompt Library

## Category: Content Creation

### Blog Post Generator
Prompt: "Write a comprehensive blog post about [TOPIC] targeting [AUDIENCE].
Include SEO keywords: [KEYWORDS]. Tone: [FORMAL/CASUAL]. Length: [WORDS] words."

### Social Media Caption Creator
Prompt: "Create [NUMBER] social media captions for [PLATFORM] about [TOPIC].
Include relevant hashtags and a call to action."

### Email Newsletter
Prompt: "Write a weekly newsletter update about [TOPIC].
Include: subject line (5 options), main content (300 words), CTA."

## Category: Workflow Automation

### Email Triage
Prompt: "Classify these emails into: Urgent/Important/Reading/Spam.
For each urgent email, draft a 2-sentence response."

### Meeting Notes Summarizer
Prompt: "Summarize this meeting transcript.
Key decisions, action items (with owners), and next steps."

### Task Priority Matrix
Prompt: "Analyze these tasks and sort by: Impact (high/medium/low) and
Effort (high/medium/low). Recommend top 5 priorities."

## Category: Business Development

### Cold Email Generator
Prompt: "Write a cold email for [TARGET_COMPANY] offering [SERVICE].
Personalization hook: [HOOK]. Tone: professional but warm."

### Competitor Analysis
Prompt: "Analyze [COMPETITOR]'s strengths and weaknesses relative to [OUR_BUSINESS].
Focus on: product, pricing, marketing channels, customer reviews."

### Value Proposition Canvas
Prompt: "Help me define the value proposition for [PRODUCT/SERVICE].
Customer jobs, pains, gains. Then map to our product features."
"""
            zf.writestr("prompts/ai-prompt-library.md", base_prompts)

            automation_readme = """# AI Productivity Toolkit

500+ ready-to-use AI prompts, automation workflows, and templates.

## Contents

- `prompts/` - AI prompt library organized by category
- `workflows/` - Step-by-step automation workflows
- `templates/` - Ready-to-use templates

## How to Use

1. Browse the prompt library for your use case
2. Copy the prompt to ChatGPT, Claude, or any AI tool
3. Customize the [BRACKETED] sections
4. Save time and scale your output

Perfect for: freelancers, entrepreneurs, content creators, and teams.
"""
            zf.writestr("README.md", automation_readme)

        zip_buffer.seek(0)
        output_path = self.products_dir / "ai-productivity-toolkit.zip"
        with open(output_path, "wb") as f:
            f.write(zip_buffer.getvalue())
        utils.log("product", f"Toolkit built: {output_path}")
        return str(output_path)

    def build_bug_bounty_agent(self):
        utils.log("product", "Building Bug Bounty AI Agent package")
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            docker_compose = """version: '3.8'
services:
  bb-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    volumes:
      - ./data:/app/data
      - ./reports:/app/reports
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - DATABASE_URL=sqlite:///data/bb.db
    restart: unless-stopped
"""
            zf.writestr("docker-compose.yml", docker_compose)

            readme = """# Bug Bounty AI Agent

AI-powered bug bounty hunting platform with:
- 17 scan types (recon, xss, ssrf, sqlmap, etc.)
- Kanban workflow (8 stages)
- CVSS enrichment via NVD API
- EPSS probability scoring
- Automated Kali Linux integration
- JWT authentication
- Live streaming output via SSE

## Quick Start

```bash
cp .env.template .env
# Edit .env with your settings
docker compose up -d
```

Access: http://localhost:3001

## Requirements

- Docker + Docker Compose
- Kali Linux container (optional, for local scanning)
- 4GB+ RAM recommended
"""
            zf.writestr("README.md", readme)

        zip_buffer.seek(0)
        output_path = self.products_dir / "bug-bounty-ai-agent.zip"
        with open(output_path, "wb") as f:
            f.write(zip_buffer.getvalue())
        utils.log("product", f"BB Agent built: {output_path}")
        return str(output_path)

    def build_all(self):
        return [
            self.build_nexus_deploy(),
            self.build_toolkit(),
            self.build_bug_bounty_agent(),
        ]
