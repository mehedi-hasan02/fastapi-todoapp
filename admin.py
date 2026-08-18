from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import model
from database import engine, SessionLocal
from model import Todos
import auth
from auth import get_current_user

route = APIRouter()


def db_connect():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(db_connect)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@route.get("/admin/todos")
def read_todos(user: user_dependency, db: db_dependency):
    if user is None or user["role"] != "admin":
        raise HTTPException(status_code=401, detail="User not authicated")

    return db.query(Todos).all()


@route.delete("/admin/deletetodo/{todo_id}")
def delete_todo(user: user_dependency, db: db_dependency, todo_id: int):
    if user is None or user["role"] != "admin":
        raise HTTPException(status_code=401, detail="User not authicated")

    todo = db.query(Todos).filter(Todos.id == todo_id).first()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.query(Todos).filter(Todos.id == todo_id).delete()

    db.commit()

    return JSONResponse(status_code=201, content="Todo deleted")
