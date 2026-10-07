from db import ENGINE
from models import Base

Base.metadata.drop_all(ENGINE)

print("Tables dropped.")