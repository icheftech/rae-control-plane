"""Run migrations and the local API using the root .env, without printing secrets."""
import os
from pathlib import Path
from dotenv import dotenv_values
from alembic.config import Config
from alembic import command
import uvicorn
root = Path(__file__).resolve().parents[1]
values = dotenv_values(root / '.env')
for key, value in values.items():
    if value is not None: os.environ.setdefault(key, value)
os.environ.setdefault('DATABASE_URL', 'postgresql://rae_user:' + values['POSTGRES_PASSWORD'] + '@127.0.0.1:55432/rae_control_plane')
import sys
sys.path.insert(0, str(root/'backend'))
os.chdir(root/'backend')
command.upgrade(Config('alembic.ini'),'head')
uvicorn.run('app.main:app', host='127.0.0.1',port=18000)
