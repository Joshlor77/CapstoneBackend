from fastapi import Depends, FastAPI, HTTPException, status
from sqlmodel import select

from routers import itemAPI
from auth import TokenAuthDep, router as authR
from models import UserRead, Location
from dependencies import SessionDep

app = FastAPI()
app.include_router(itemAPI.router)
app.include_router(authR)

@app.get("/user")
async def user_details(session: SessionDep, current_user: TokenAuthDep):    
    return current_user.model_dump(include=UserRead.model_fields.keys())

@app.get("/locations")
async def read_locations(session: SessionDep, current_user: TokenAuthDep):
    statement = select(Location)
    locations = session.exec(statement).all()
    return locations
