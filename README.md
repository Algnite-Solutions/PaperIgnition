# PaperIgnition Demo
This project implements a simple H5 Version PaperIgnition front/backend UI assuming LLM is hosted on a remote machine (e.g. vLLM backend).

## Prerequisites

Before you begin, ensure you have Node.js and npm (or yarn) installed on your system.

- **AIgnite**: refer instruction in the repo.
- **PostgreSQL**: Install PostgreSQL 12+ (Linux/OS X/Windows)
- **python dependencies**: `pip install -r requirements.txt`

```bash
export PYTHONPATH=/Users/bran/Desktop/AIgnite-Solutions/AIgnite/src:/Users/bran/Desktop/AIgnite-Solutions/PaperIgnition
$env:PYTHONPATH = "D:\PaperIgnition\PaperIgnition"
```
## Initialize Databases (DB Backend)

In the PaperIgnition rootfolder, perform followings steps w.r.t. 
1. Init User DB
source code: backend/user_db/
```
# create role (MAC)
psql postgres
CREATE ROLE postgres WITH LOGIN SUPERUSER;

# create test user (MAC)
CREATE USER test_user WITH PASSWORD '11111' CREATEDB LOGIN;
CREATE DATABASE test_user OWNER test_user;

# create user database
psql -U test_user 
CREATE DATABASE test_user_db;

python scripts/user_db_init.py

```

2. Create DB Backend
```
CREATE DATABASE test_metadata_db;
```

3. Init index service for development
source code: backend/scripts/
```
bash launch_test_service.sh
```



## Start Web Backend

backend/app
```
 # 开发环境
 uvicorn backend.app.main:app --reload --port 8000
 # 生产环境
 uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```