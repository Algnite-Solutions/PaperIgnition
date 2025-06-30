# PaperIgnition H5 Version
This project implements a simple H5 Version PaperIgnition front/backend UI assuming LLM is hosted on a remote machine (e.g. vLLM backend).

## Prerequisites

Before you begin, ensure you have Node.js and npm (or yarn) installed on your system.

- **Node.js**:  v20.10.0+
- **npm**: 10.2.3+
- **AIgnite**: refer instruction in the repo.
- **PostgreSQL**: Install PostgreSQL 12+ (Linux/OS X/Windows)
- **python dependencies**: `pip install -r requirements.txt`

You can verify your Node.js and npm versions by running:
```bash
node -v
npm -v
```

Install pnpm `npm install -g pnpm`

export PYTHONPATH=/path/to/your/PaperIgnition

## Initialize Databases (DB Backend)
In the PaperIgnition rootfolder, perform followings steps. 
1. Init User DB
source code: backend/user_db/
```
createdb AIgnite
# create role
psql postgres
CREATE ROLE postgres WITH LOGIN SUPERUSER;

python backend/user_db_service/db_init.py
```

2. Init PaperDB (TODO)
source code: backend/paper_db/


3. Start DB Backend

## Start Web Backend
backend/app
```
 # 开发环境
 uvicorn backend.app.main:app --reload --port 8000
 # 生产环境
 uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Start Frontend
```
cd frontend
pnpm install
pnpm run dev:h5
```

## Orchestrator
PaperIgnition orchestrator runs regularly to update the paperDB and generate user recommendations.
```
mkdir -p ./orchestrator/blogs/
python orchestrator/run_all.py
```


## API Endpoints
Please document endpoint for each APIs, e.g. IndexService, UserDBService