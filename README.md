# PaperIgnition Service

This project implements a simple front/backend UI assuming LLM is hosted on a remote machine (e.g. vLLM backend).

## Setup

1. Install AIgnite:
Please refer to https://github.com/Algnite-Solutions/AIgnite for installation

2. Provide API keys, server URL in `.env`

3. Run the service:
For example, launch indexing server
```bash
uvicorn backend.index_service.main:app --reload
```

## API Endpoints
Please document endpoint for each APIs