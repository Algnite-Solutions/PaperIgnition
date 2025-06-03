# PaperIgnition Service

This project implements a simple front/backend UI assuming LLM is hosted on a remote machine (e.g. vLLM backend).

## Setup

1. Install AIgnite:
Please refer to https://github.com/Algnite-Solutions/AIgnite for `pip` installation

2. Provide API keys, server URL in `.env`

3. 
```
export PYTHONPATH=$YOUR_PAPERIGNITION_PATH
```

4. Run the service:
First, launch indexing server
```bash
uvicorn backend.index_service.main:app --reload
```

Then, test orchestrator
```
mkdir -p ./orchestrator/blogs/
python orchestrator/run_all.py
```


## API Endpoints
Please document endpoint for each APIs