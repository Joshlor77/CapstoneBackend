from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response, File
from datetime import datetime
from sqlmodel import select

from ..models import ItemType, ItemCreateForm, Item, ItemNoImageView, ItemSearchParam, ItemUpdate, User, UserRead
from ..dependencies import SessionDep, CommonQueryParams
from ..auth import TokenAuthDep

router = APIRouter(tags=["Item"])

@router.get("/itemTypes")
async def get_itemTypes(session: SessionDep, current_user: TokenAuthDep):
    statement = select(ItemType)
    results = session.exec(statement)
    return results.all()

@router.post("/item")
async def intake_item(session: SessionDep, current_user: TokenAuthDep, item_data: Annotated[ItemCreateForm, Depends()], file: Annotated[bytes, File()]):
    item = Item(serial=item_data.serial, part=item_data.part, loc_id=item_data.loc_id, item_type=item_data.item_type, image=file, last_user=current_user.user_id, last_updated=datetime.today(), madlib=item_data.madlib)
    session.add(item)
    session.commit()

    session.refresh(item)
    return item.model_dump(include=ItemNoImageView.model_fields.keys())

@router.get("/item")
async def search_items(session: SessionDep, commons: Annotated[CommonQueryParams, Depends(CommonQueryParams)], current_user: TokenAuthDep, itemQ: Annotated[ItemSearchParam | None, Depends(ItemSearchParam)]):
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
    statement = statement.offset(commons.skip).limit(commons.limit)

    items = session.exec(statement).all()
    item_dicts = [
        item.model_dump(exclude={"last_user"}) | {"last_user": item.recent_user.model_dump(include=UserRead.model_fields.keys())}
        for item in items
    ]
    return item_dicts

@router.get("/item/image/{item_id}")
async def get_item_image(session: SessionDep, current_user: TokenAuthDep, item_id: int):
    statement = select(ItemNoImageView).where(Item.item_id == item_id)
    result = session.exec(statement)
    item = result.one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
            headers={"error": "Item not found"}
        )
    return Response(content=item.image, media_type="image/png")

#TODO
@router.patch("/item/move/{item_id}")
async def move_item(session: SessionDep, current_user: TokenAuthDep, item_id: int, itemfields: ItemUpdate):
    pass

#TODO
@router.patch("/item/ship/{item_id}")
async def ship_item(session: SessionDep, current_user: TokenAuthDep, item_id: int, address: str):
    pass