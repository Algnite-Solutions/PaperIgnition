
# 🧠 Index Service Setup Guide

This guide explains how to configure and run the Index Service by properly setting up the three required databases:

- **MetadataDB** (PostgreSQL)
- **VectorDB** (Faiss)
- **PhotoDB** (MinIO)

Ensure all three are initialized and configured before running the service.  
Refer to `tests/config.yaml` for example configuration.

To start indexing service:
```bash
bash scripts/launch_index_service.sh 
```

---

## 1️⃣ MetadataDB (PostgreSQL)

### ✅ Install PostgreSQL

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### ▶️ Start & Connect

```bash
sudo service postgresql start
sudo -u postgres psql
```

### 🛠 Create Database

Inside `psql`:

```sql
CREATE DATABASE paperignition;
```

### 🔐 Set User Password (Optional)

If using the default config:

```yaml
user: postgres
password: 11111
```

Run:

```sql
ALTER USER postgres WITH PASSWORD '11111';
```

### 🧱 Create Tables (Example) should be deleted

```sql
\c paperignition;

CREATE TABLE papers (
    paper_id SERIAL PRIMARY KEY,
    title TEXT,
    authors TEXT,
    abstract TEXT,
    publication_date DATE,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

> Add additional tables (e.g., for chunks or images) as needed.

### 🧪 Test DB Connection

```python
from sqlalchemy import create_engine

engine = create_engine('postgresql://postgres:11111@localhost:5432/aignite_test')
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print(result.fetchone())  # Expected output: (1,)
```

---

## 2️⃣ VectorDB (Faiss)

### ✅ Install Faiss

Faiss is installed automatically if you have set up `AIgnite` dependencies correctly. If not:

```bash
pip install faiss-cpu
```

### 📁 Prepare Storage

Create the directory for storing vector index files:

```bash
mkdir -p vector_db/test_db
```

Make sure this path is referenced in your `config.yaml` as:

```yaml
vector_db:
  db_path: "vector_db/test_db"
```

---

## 3️⃣ PhotoDB (MinIO)

### ✅ Install MinIO

```bash
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/
```

Verify installation:

```bash
minio --version
```

### 📁 Create Data Directory

```bash
mkdir ~/minio_data
```

### 🚀 Start MinIO Server

```bash
minio server ~/minio_data --address :9081 --console-address :9091
```

- Access API at: `http://localhost:9081`
- Web console: [http://localhost:9091](http://localhost:9091)

### 🔑 Access Console & Configure

1. Visit [http://localhost:9091](http://localhost:9091)  
2. Login using your **Access Key** and **Secret Key**  
3. Create a bucket (e.g., `aignite-test-papers`)  
4. Use the credentials and bucket name in your `config.yaml`:

```yaml
minio_db:
  endpoint: 'localhost:9081'
  access_key: 'your-access-key'
  secret_key: 'your-secret-key'
  bucket_name: 'aignite-test-papers'
  secure: false
```

---
