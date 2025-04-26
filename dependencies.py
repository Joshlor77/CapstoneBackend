from typing import Annotated

from sqlmodel import Session, create_engine
from fastapi import Depends

from .models import User

# DATABASE_URL = "mysql+pymysql://admin:GamblingSucks!234@capstonedatabase.czcso2wimnbr.us-east-2.rds.amazonaws.com:3306/TestSchema"
DATABASE_URL = "mysql+pymysql://admin:GamblingSucks!234@localhost:3306/BackendTestSchema"

engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

class CommonQueryParams:
    def __init__(self, skip: int = 0, limit: int = 10):
        self.skip = skip
        self.limit = limit
