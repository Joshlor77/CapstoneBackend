from typing import Annotated
from datetime import datetime, timedelta, timezone
import jwt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlmodel import Session, select
from pydantic import BaseModel
from passlib.context import CryptContext

from .dependencies import SessionDep
from .models import User

#Removes error about bcrypt version
import bcrypt
bcrypt.__about__ = bcrypt

router = APIRouter(tags=["Auth"])

SECRET_KEY = "8ee8fa5e2bdfad14e2b01dec5775e5582d74ee2e091ef97620c0df8324c9e203"
ALGORITHM = "HS256"
ACCCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="Token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str, session: Session):
    statement = select(User).where(User.username==username)
    result = session.exec(statement)
    return result.one_or_none()
    
def authenticate_user(username: str, password: str, session: Session):
    user = get_user(username, session)
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

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to validate credentials",
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
    user = get_user(username=token_data.username, session=session)
    if user is None:
        raise credentials_exception
    return user

#Implement a refresh token
@router.post("/Token")
async def user_auth(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> Token:
    user = authenticate_user(form_data.username, form_data.password, session)
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

@router.post("/register")
async def user_register(first: str, last: str, username: str, password: str, session: SessionDep):
    if len(session.exec(select(User).where(User.username==username)).all()) != 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
            headers={"error": "username_taken"}
        )
    hashedPass = pwd_context.hash(password)
    user = User(first=first, last=last, username=username, password=hashedPass)
    session.add(user)
    session.commit()
    session.refresh(user)
    return HTTPException(
        statu_code=status.HTTP_200_OK,
        detail="Successfully Registered"
    )

TokenAuthDep = Annotated[User, Depends(get_current_user)]