import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://soccer_user:soccer_password@127.0.0.1:3306/soccer_events"
)

ENGINE = create_engine(DATABASE_URL)

Session = sessionmaker(bind=ENGINE)

def make_session():
    return Session()