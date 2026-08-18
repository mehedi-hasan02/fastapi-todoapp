from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import model
from database import engine, SessionLocal
from model import Todos, Users
import auth
from auth import get_current_user
import admin


class Todo(BaseModel):
    title: str
    description: str = Field(max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[int] = Field(default=None, gt=0, lt=6)
    complete: Optional[bool] = Field(default=None)


app = FastAPI()


model.Base.metadata.create_all(bind=engine)
app.include_router(auth.route)
app.include_router(admin.route)


def db_connect():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(db_connect)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.get("/")
def read_todo(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authicated")
    return db.query(Todos).filter(Todos.owner_id == user["id"]).all()


@app.get("/todo/id")
def read_specific_tod(user: user_dependency, db: db_dependency, id: int):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authicated")
    return (
        db.query(Todos)
        .filter(Todos.owner_id == user["id"])
        .filter(Todos.id == id)
        .first()
    )


@app.post("/create")
def add_todo(user: user_dependency, db: db_dependency, new_todo: Todo):
    todo_model = Todos(**new_todo.model_dump(), owner_id=user["id"])

    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)

    return todo_model


@app.put("/update/{todo_id}")
def update_todo(
    user: user_dependency, db: db_dependency, todo_id: int, update_todo: TodoUpdate
):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authicated")
    todo = (
        db.query(Todos)
        .filter(Todos.owner_id == user["id"])
        .filter(Todos.id == todo_id)
        .first()
    )

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    update_data = update_todo.model_dump()

    for key, value in update_data.items():
        setattr(todo, key, value)

    db.commit()


@app.delete("/delete/{todo_id}")
def delete_todo(user: user_dependency, db: db_dependency, id: int):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authicated")

    todo = (
        db.query(Todos)
        .filter(Todos.owner_id == user["id"])
        .filter(Todos.id == id)
        .first()
    )

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.query(Todos).filter(Todos.owner_id == user["id"]).filter(Todos.id == id).delete()

    db.commit()

    return JSONResponse(
        status_code=200, content={"message": "Todo delete successfully"}
    )


@app.get("/user")
def get_user(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return db.query(Users).filter(Users.email == user["email"]).first()
