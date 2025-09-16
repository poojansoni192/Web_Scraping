from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import psycopg2
from typing import List
from fastapi import Query

app = FastAPI()

# Dummy in-memory "database"
fake_users_db = {}

# Password hashing using argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT Config
SECRET_KEY = "my_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Database connection setup
DATABASE_CONFIG = {
    'dbname': 'books_db',
    'user': 'postgres',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

def connect_to_db():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    return conn

# Models
class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Book(BaseModel):
    title: str
    price: str
    availability: str
    rating: str

# Utility Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Auth Dependency
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Routes
@app.post("/signup")
def signup(user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = hash_password(user.password)
    fake_users_db[user.username] = {"username": user.username, "hashed_password": hashed_pw}
    return {"msg": "User created successfully"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}

# Function to fetch books from the PostgreSQL database
def get_books_from_db():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, availability, rating FROM books")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    books = []
    for row in rows:
        books.append({"title": row[0], "price": row[1], "availability": row[2], "rating": row[3]})
    return books

# Function to insert a new book into the database
def add_book_to_db(book: Book):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, price, availability, rating) VALUES (%s, %s, %s, %s)",
        (book.title, book.price, book.availability, book.rating)
    )
    conn.commit()
    cursor.close()
    conn.close()


# Secure /books endpoint that fetches real data from the database
@app.get("/books/", response_model=List[Book])
def get_books(current_user: str = Depends(get_current_user)):
    books = get_books_from_db()
    return books

# POST endpoint to add a new book
@app.post("/books/", status_code=201)
def create_book(book: Book, current_user: str = Depends(get_current_user)):
    add_book_to_db(book)
    return {"msg": "Book added successfully"}

@app.delete("/books/{book_id}")
def delete_book(book_id: int, current_user: str = Depends(get_current_user)):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
    book = cursor.fetchone()
    if not book:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")

    cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"msg": f"Book with ID {book_id} has been deleted"}

@app.get("/books/search", response_model=List[Book])
def search_books(title: str = Query(..., min_length=1), current_user: str = Depends(get_current_user)):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, availability, rating FROM books WHERE LOWER(title) LIKE %s", (f"%{title.lower()}%",))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="No matching books found")

    books = [{"title": row[0], "price": row[1], "availability": row[2], "rating": row[3]} for row in rows]
    return books
