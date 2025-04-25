from datetime import datetime, timedelta, timezone

from typing import Annotated
import jwt
from fastapi import Depends, FastAPI, File, UploadFile, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

#This removes the error message about bcrypt version
import bcrypt
bcrypt.__about__ = bcrypt

SECRET_KEY = "8ee8fa5e2bdfad14e2b01dec5775e5582d74ee2e091ef97620c0df8324c9e203"
ALGORITHM = "HS256"
ACCCESS_TOKEN_EXPIRE_MINUTES = 30
# DATABASE_URL = "mysql+pymysql://admin:GamblingSucks!234@capstonedatabase.czcso2wimnbr.us-east-2.rds.amazonaws.com:3306/TestSchema"
DATABASE_URL = "mysql+pymysql://admin:GamblingSucks!234@localhost:3306/TestSchema"

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class CommonQueryParams:
    def __init__(self, skip: int = 0, limit: int = 10):
        self.skip = skip
        self.limit = limit
    
class User(SQLModel, table=True):
    __tablename__ = "User"

    user_id: int = Field(primary_key=True)
    first: str
    last: str
    username: str = Field(unique=True)
    password: str

class Building(SQLModel, table=True):
    __tablename__ = "Building"

    building_id: int = Field(primary_key=True)
    name: str
    address: str

class Location(SQLModel, table=True):
    __tablename__ = "Location"

    loc_id: int = Field(primary_key=True)
    building_id: int = Field(foreign_key="Building.building_id")
    name: str

class ItemType(SQLModel, table=True):
    __tablename__ = "ItemType"

    type_name: str = Field(primary_key=True)

class ItemSearchParam:
    def __init__(self, item_id: int | None = None, item_type: str | None = None, loc_id: int | None = None, serial: str | None = None, part: str | None = None):
        self.item_id = item_id
        self.item_type = item_type
        self.loc_id = loc_id
        self.serial = serial
        self.part = part

class ItemCreateForm:
    def __init__(self, item_type: Annotated[str, Form()], loc_id: Annotated[int, Form()], serial: Annotated[str, Form()], part: Annotated[str, Form()]):
        self.item_type = item_type
        self.loc_id = loc_id
        self.serial = serial
        self.part = part

class ImageUpdate(BaseModel):
    loc_id: int | None = Field(default=None, foreign_key="Location.loc_id")
    last_user: str
    last_updated: str
    madlib: str

class ItemNoImageView(ImageUpdate, table=True):
    __tablename__ = "ItemNoImage"
    item_id: int = Field(primary_key=True)
    item_type: str = Field(foreign_key="ItemType.type_name")
    loc_id: int | None = Field(default=None, foreign_key="Location.loc_id")
    serial: str
    part: str
    
class Item(ItemNoImageView, table=True):
    __tablename__ = "Item"

    image: bytes | None = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="Token")

engine = create_engine(DATABASE_URL)
app = FastAPI()

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str):
    with Session(engine) as session:
        statement = select(User).where(User.username==username)
        result = session.exec(statement)
        return result.one_or_none()
    
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
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
async def root():
    return {"Message": "Hello"}

#Implement a refresh token
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
async def user_auth(first: str, last: str, username: str, password: str, session: SessionDep):
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
    return user

@app.get("/user")
async def read_name(session: SessionDep, current_user: Annotated[User, Depends(get_current_user)]):
    return {"first": current_user.first, "last": current_user.last}

@app.get("/itemTypes")
async def get_itemTypes(session: SessionDep, current_user: Annotated[User, Depends(get_current_user)]):
    statement = select(ItemType)
    results = session.exec(statement)
    return results.all()

@app.post("/item")
async def create_item(session: SessionDep, current_user: Annotated[User, Depends(get_current_user)], item_data: Annotated[ItemCreateForm, Depends()], file: Annotated[bytes, File()]):
    item = Item(serial=item_data.serial, part=item_data.part, loc_id=item_data.loc_id, item_type=item_data.item_type, image=file)
    session.add(item)
    session.commit()
    return HTTPException(
        status_code=status.HTTP_201_CREATED,
        detail="Item created successfully",
        headers={"message": "Success"}
    )

@app.get("/item")
async def read_items(session: SessionDep, commons: Annotated[CommonQueryParams, Depends(CommonQueryParams)], current_user: Annotated[User, Depends(get_current_user)], itemQ: Annotated[ItemSearchParam | None, Depends(ItemSearchParam)]):
    statement = select(ItemNoImageView)
    if itemQ.item_id is not None:
        statement = statement.where(ItemNoImageView.item_id == itemQ.item_id)
    if itemQ.serial is not None:
        statement = statement.where(ItemNoImageView.serial == itemQ.serial)
    if itemQ.part is not None:
        statement = statement.where(ItemNoImageView.part == itemQ.part)
    if itemQ.item_type is not None:
        statement = statement.where(ItemNoImageView.item_type == itemQ.item_type)
    if itemQ.loc_id is not None:
        statement = statement.where(ItemNoImageView.loc_id == itemQ.loc_id)
    results = session.exec(statement)

    return results.all()[commons.skip : commons.skip + commons.limit]

@app.get("/item/{item_id}/image")
async def read_item_image(session: SessionDep, current_user: Annotated[User, Depends(get_current_user)], item_id: int):
    statement = select(Item).where(Item.item_id == item_id)
    result = session.exec(statement)
    item = result.one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
            headers={"error": "Item not found"}
        )
    return Response(content=item.image, media_type="image/png")

@app.patch("/item")
async def update_item(session: SessionDep, current_user: Annotated[User, Depends(get_current_user)]):
    pass

@app.get("/locations")
async def read_locations(session: SessionDep, current_user: Annotated[User, Depends(get_current_user)]):
    statement = select(Location)
    locations = session.exec(statement).all()
    return locations
