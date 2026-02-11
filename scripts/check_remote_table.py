#!/usr/bin/env python3
"""Check remote table structure - shows actual column names with case"""
import yaml
import psycopg2

config_path = "orchestrator/production_config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
aliyun_config = config['aliyun_rds']

conn = psycopg2.connect(
    host=aliyun_config['db_host'],
    port=int(aliyun_config['db_port']),
    user=aliyun_config['db_user'],
    password=aliyun_config['db_password'],
    database=aliyun_config.get('db_name_paper', 'paperignition')
)

cursor = conn.cursor()

# Query pg_attribute to get actual column names (with case)
cursor.execute("""
    SELECT a.attname AS column_name,
           pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
    FROM pg_catalog.pg_attribute a
    JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
    JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
    WHERE n.nspname = 'public'
    AND c.relname = 'papers'
    AND a.attnum > 0
    AND NOT a.attisdropped
    ORDER BY a.attnum;
""")

print("Remote papers table columns (actual names):")
for row in cursor.fetchall():
    print(f"  '{row[0]}': {row[1]}")

cursor.close()
conn.close()

