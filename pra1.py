from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Union, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2
import os

# ----------------------------- #
#         INITIAL SETUP         #
# ----------------------------- #

load_dotenv()  # Load environment variables

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ----------------------------- #
#        CONFIG & SECURITY      #
# ----------------------------- #

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # bcrypt used here

# Dummy in-memory "database" for demo
fake_users_db = {}

# ----------------------------- #
#         DATABASE SETUP        #
# ----------------------------- #

DATABASE_CONFIG = {
    'dbname': 'books_db',
    'user': 'postgres',
    'password': 'Monday@2025',
    'host': 'localhost',
    'port': 5432
}

def connect_to_db():
    return psycopg2.connect(**DATABASE_CONFIG)

# ----------------------------- #
#           MODELS              #
# ----------------------------- #

class User(BaseModel):
    username: str
    password: str

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str
    role: Optional[str] = None  # Extendable for roles

class Book(BaseModel):
    title: str
    price: str
    availability: str
    rating: str

# ----------------------------- #
#         UTILITY FUNCS         #
# ----------------------------- #

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Check expiration explicitly if needed
        if payload.get("exp") and datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow():
            return None
        return payload
    except JWTError:
        return None

# ----------------------------- #
#          DEPENDENCIES         #
# ----------------------------- #

def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenData(**payload)

def get_current_active_user(current_user: TokenData = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

# ----------------------------- #
#            ROUTES             #
# ----------------------------- #

@app.post("/signup")
def signup(user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = hash_password(user.password)
    fake_users_db[user.username] = {
        "username": user.username,
        "hashed_password": hashed_pw,
        "role": "admin"  # Default role (you can change as needed)
    }
    return {"msg": "User created successfully"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token_data = {"sub": form_data.username, "role": user.get("role", "user")}
    access_token = create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/books/", response_model=List[Book])
def get_books(current_user: TokenData = Depends(get_current_user)):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, availability, rating FROM books")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {"title": row[0], "price": row[1], "availability": row[2], "rating": row[3]}
        for row in rows
    ]
