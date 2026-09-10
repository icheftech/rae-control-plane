"""Apply local migrations and assert pre-existing audit hashes were preserved."""
import os
import sys
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

root=Path(__file__).resolve().parents[1]
values=dotenv_values(root/'.env')
for key,value in values.items():
    if value is not None:
        os.environ.setdefault(key,value)
os.environ.setdefault('DATABASE_URL','postgresql://rae_user:'+values['POSTGRES_PASSWORD']+'@127.0.0.1:55432/rae_control_plane')
engine=create_engine(os.environ['DATABASE_URL'])
with engine.connect() as db:
    before=db.execute(text('SELECT sequence_number,event_hash FROM audit_events ORDER BY sequence_number')).all()
sys.path.insert(0,str(root/'backend'))
os.chdir(root/'backend')
command.upgrade(Config('alembic.ini'),'head')
with engine.connect() as db:
    after=db.execute(text('SELECT sequence_number,event_hash FROM audit_events ORDER BY sequence_number')).all()
assert before == after, 'Unexpected audit hash change during migration'
engine.dispose()
print(f'Migrations applied. Preserved all {len(before)} existing audit hashes.')
