from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI
from mangum import Mangum

DATABASE_URL = "mysql+pymysql://admin:GamblingSucks!234@capstonedatabase.czcso2wimnbr.us-east-2.rds.amazonaws.com:3306/TestSchema"

class User(SQLModel, table=True):
    uID: int = Field(primary_key=True)
    first: str
    last: str
    username: str
    password: str

engine = create_engine(DATABASE_URL, echo=True)

app = FastAPI()
handler = Mangum(app)

@app.get("/user/{userID}")
def get_user(userID):
    with Session(engine) as session:
        statement = select(User).where(User.uID == userID)
        results = session.exec(statement)
        users = results.all()
        if not users:
            return None
        return users[0]