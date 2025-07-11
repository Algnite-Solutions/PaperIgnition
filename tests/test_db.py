from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:11111@localhost:5432/paperignition')
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.fetchone())  # Expected output: (1,)