import requests 
from bs4 import BeautifulSoup
import psycopg2


DATABASE_CONFIG ={
    'dbname': 'books_db',
    'user': 'postgres',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

def connect_to_db():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    return conn

def create_table():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            price VARCHAR(100),
            availability VARCHAR(255),
            rating VARCHAR(50)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()


def insert_book_to_db(book):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO books (title, price, availability, rating)
        VALUES (%s, %s, %s, %s );
    """, (book['Title'], book['Price'], book['Availability'], book['Rating']))
    conn.commit()
    cursor.close()
    conn.close()



def scrape_books(page_url):
    response=requests.get(page_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    books = soup.find_all('article', class_='product_pod')

    for book in books:
        title = book.find('h3').find('a')['title']
        price = book.find('p', class_='price_color').text
        availability = book.find('p',class_='instock availability').text.strip()
        rating = book.find('p', class_='star-rating')['class'][1]
        
        book_data = {
        'Title': title,
        'Price': price,
        'Availability': availability,
        'Rating': rating,
    }

        insert_book_to_db(book_data)
        print(f"Inserted: {title} | {price} | {availability} | {rating}")

def scrape_all_books():
    create_table()
    base_url = "http://books.toscrape.com/catalogue/category/books/mystery_3/page-{}.html"

    for page_num in range(1,3):
        if page_num == 1:
            page_url = "http://books.toscrape.com/catalogue/category/books/mystery_3/index.html"
        else:
            page_url = base_url.format(page_num)
        print(f"Scraping page {page_num}: {page_url}")
        scrape_books(page_url)


scrape_all_books()