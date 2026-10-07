from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ENGINE = create_engine(
    "mysql+pymysql://soccer_user:soccer_password@127.0.0.1:3306/soccer_events"
)

Session = sessionmaker(bind=ENGINE)


def make_session():
    return Session()