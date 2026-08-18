from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from model import Users
from database import engine, SessionLocal
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone

SECRET_KEY = "53206f05c2780cb99c9359264f17531e87b808305a2dc303724e9be6b99e09f7"
ALGORITHM = "HS256"

route = APIRouter()

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
OAuth2Bearer = OAuth2PasswordBearer(tokenUrl="login")


class CreateUsers(BaseModel):
    email: str = Field(max_length=30)
    name: str = Field(max_length=30)
    password: str
    role: str
    phone_number: str


class userUpdate(BaseModel):
    email: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None, max_length=100)
    phone_number: Optional[str] = Field(default=None)


class UpdatePassword(BaseModel):
    current_pass: str
    new_pass: str


def authentication(email, password, db):
    user = db.query(Users).filter(Users.email == email).first()

    if not user:
        return False

    match = bcrypt_context.verify(password, user.password)

    if not match:
        return False

    return user


def generate_token(email: str, user_id: int, role: str, expiretime: timedelta):
    encode = {"sub": email, "id": user_id, "role": role}
    expire = datetime.now(timezone.utc) + expiretime
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Annotated[str, Depends(OAuth2Bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        email = payload.get("sub")
        user_id = payload.get("id")
        role = payload.get("role")

        if email is None or user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"email": email, "id": user_id, "role": role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


user_dependency = Annotated[dict, Depends(get_current_user)]


def db_connect():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(db_connect)]


@route.post("/createuser")
def create_user(db: db_dependency, new_user: CreateUsers):
    user = Users(
        email=new_user.email,
        name=new_user.name,
        password=bcrypt_context.hash(new_user.password),
        role=new_user.role,
        is_active=True,
        phone_number=new_user.phone_number,
    )

    db.add(user)
    db.commit()

    return JSONResponse(status_code=200, content={"message": "User create successful"})


@route.post("/login")
def login_user(
    db: db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):

    user = authentication(form_data.username, form_data.password, db)

    if not user:
        return "User not authenticate"

    token = generate_token(user.email, user.id, user.role, timedelta(minutes=30))

    return {"access_token": token, "token_type": "bearer"}


@route.put("/edituser")
def update_todo(user: user_dependency, db: db_dependency, update_user: userUpdate):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authicated")
    user = db.query(Users).filter(Users.id == user["id"]).first()

    update_data = update_user.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()


@route.put("/updatepass")
def update_password(
    user: user_dependency, db: db_dependency, update_pass: UpdatePassword
):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authicated")
    userData = db.query(Users).filter(Users.id == user["id"]).first()

    if not bcrypt_context.verify(update_pass.current_pass, userData.password):
        raise HTTPException(status_code=401, detail="Password wrong")

    userData.password = bcrypt_context.hash(update_pass.new_pass)

    db.add(userData)

    db.commit()

    return JSONResponse(status_code=201, content={"message": "Password updated"})
