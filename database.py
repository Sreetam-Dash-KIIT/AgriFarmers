import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "agriconnect.db")


def get_database():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_database()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            crop TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            location TEXT NOT NULL,
            FOREIGN KEY (farmer_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buyer_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(buyer_id, product_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL UNIQUE,
            vehicle_type TEXT NOT NULL,
            vehicle_number TEXT NOT NULL UNIQUE,
            capacity REAL NOT NULL,
            fuel_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()

    print("Database created successfully!")
    print("Database location:", DB_PATH)


if __name__ == "__main__":
    create_database()
