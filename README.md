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

Install pnpm `sudo npm install -g pnpm`

export PYTHONPATH=/path/to/your/PaperIgnition

## Initialize Databases (DB Backend)

In the PaperIgnition rootfolder, perform followings steps. 
1. Init User DB
source code: backend/user_db/
```
# create role (MAC)
psql postgres
CREATE ROLE postgres WITH LOGIN SUPERUSER;

# create role (ubuntu)
sudo service postgresql start
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD '11111';

# create user database
CREATE DATABASE paperignition_user;

python scripts/user_db_init.py
```

2. Start DB Backend
```
CREATE DATABASE paperignition;

python scripts/paper_db_init.py
```

3. Init Index Service and test
source code: backend/index_service/
```
bash launch_index_service.sh
python tests/test_api_endpoints.py
```



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