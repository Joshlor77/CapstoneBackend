from sqlmodel import SQLModel, Relationship, Field
from pydantic import BaseModel
from typing import Annotated, Optional
from fastapi import Form

class UserRead(SQLModel):
    user_id: int = Field(primary_key=True)
    last: str
    first: str

class User(UserRead, SQLModel, table=True):
    __tablename__ = "User"

    username: str = Field(unique=True)
    password: str

    items: list["ItemNoImageView"] = Relationship(back_populates="recent_user")

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
    def __init__(self, item_type: Annotated[str, Form()], loc_id: Annotated[int, Form()], serial: Annotated[str, Form()], part: Annotated[str, Form()], madlib:  Annotated[str, Form()]):
        self.item_type = item_type
        self.loc_id = loc_id
        self.serial = serial
        self.part = part
        self.madlib = madlib

class ItemMove(BaseModel):
    loc_id: int
    madlib: str

class ItemNoImageView(SQLModel, table=True):
    __tablename__ = "ItemNoImageView"
    item_id: int = Field(primary_key=True)
    item_type: str = Field(foreign_key="ItemType.type_name")
    loc_id: int | None = Field(default=None, foreign_key="Location.loc_id")
    serial: str
    part: str
    last_user: int = Field(foreign_key="User.user_id")
    last_updated: str
    madlib: str

    recent_user: User | None = Relationship(back_populates="items", sa_relationship_kwargs=dict(lazy="selectin"))

class Item(SQLModel, table=True):
    __tablename__ = "Item"
    item_id: int = Field(primary_key=True)
    item_type: str = Field(foreign_key="ItemType.type_name")
    loc_id: int | None = Field(default=None, foreign_key="Location.loc_id")
    serial: str
    part: str
    last_user: int = Field(foreign_key="User.user_id")
    last_updated: str
    madlib: str
    image: bytes | None = None

    shipment: Optional["Shipment"] = Relationship(back_populates="item")


class Shipment(SQLModel, table=True):
    __tablename__ = "Shipment"
    shipment_id: int = Field(primary_key=True)
    item_id: int = Field(foreign_key="Item.item_id")
    ship_date: str | None = None
    deliver_date: str | None = None
    created_date: str
    address: str

    item: Optional[Item] = Relationship(back_populates="shipment")
