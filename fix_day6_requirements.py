from pathlib import Path

content = '''fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic[email]==2.9.2
pydantic-settings==2.5.2
sqlalchemy==2.0.35
psycopg[binary]==3.2.3
redis==5.0.8
python-dotenv==1.0.1
alembic==1.13.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
python-multipart==0.0.12
langgraph==0.2.45
langchain-core==0.3.15
httpx==0.27.2
'''

Path("backend/requirements.txt").write_text(content, encoding="utf-8")
print("Wrote backend/requirements.txt")