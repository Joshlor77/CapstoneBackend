from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from mangum import Mangum
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

SECRET_KEY = "8ee8fa5e2bdfad14e2b01dec5775e5582d74ee2e091ef97620c0df8324c9e203"
ALGORITHM = "HS256"
ACCCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = "mysql+pymysql://admin:GamblingSucks!234@capstonedatabase.czcso2wimnbr.us-east-2.rds.amazonaws.com:3306/TestSchema"

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
    
class User(SQLModel, table=True):
    uID: int = Field(primary_key=True)
    first: str
    last: str
    username: str
    password: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="Token")

engine = create_engine(DATABASE_URL)

app = FastAPI()
handler = Mangum(app)

# def get_session():
#     with Session(engine) as session:
#         yield session

#SessionDep = Annotated[Session, Depends(get_session)]

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str):
    with Session(engine) as session:
        statement = select(User).where(User.username==username)
        result = session.exec(statement)
        r = result.all()
        if not r:
            return None
        return r[0]
        
def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to validate crednetials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/Token")
async def user_auth(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data = {"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.post("/user/register")
async def user_auth(first: str, last: str, username: str, password: str):
    with Session(engine) as session:
        hashedPass = pwd_context.hash(password)
        user = User(first=first, last=last, username=username, password=hashedPass)
        session.add(user)
        session.commit()
        return user
    
@app.get("/test")
async def jwtTest(current_user: Annotated[User, Depends(get_current_user)]):
    return [{"Message": "JWT Authentication Success!"}]