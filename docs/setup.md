# Setup Guide

## Status

This document is a Phase 1 placeholder. Exact installation and startup commands
will be added when the backend, frontend, and containers are implemented.

## Target Environment

- Linux Mint
- NVIDIA GPU with supported drivers
- Docker and Docker Compose
- Ollama
- Python for local backend development
- Node.js and npm for local frontend development

## Planned Setup Flow

1. Install and verify the NVIDIA drivers.
2. Install Ollama and pull a small model such as `qwen3:4b`.
3. Create local environment files from the committed `.env.example` files.
4. Install backend and frontend dependencies.
5. Start the backend and frontend locally, or use Docker Compose.
6. Verify the health endpoint and Ollama connectivity.

No secrets will be committed to source control.
