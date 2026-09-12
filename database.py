import os
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.environ.get("DATABASE_URL")


def get_database():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Please create a PostgreSQL database and set the DATABASE_URL environment variable."
        )

    connection = psycopg2.connect(DATABASE_URL)
    return connection


def create_database():
    connection = get_database()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('farmer', 'buyer', 'driver')),
            location TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            farmer_id INTEGER,
            crop TEXT NOT NULL,
            quantity DOUBLE PRECISION NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            location TEXT NOT NULL,
            FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE (buyer_id, product_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id SERIAL PRIMARY KEY,
            driver_id INTEGER NOT NULL UNIQUE,
            vehicle_type TEXT NOT NULL,
            vehicle_number TEXT NOT NULL UNIQUE,
            capacity DOUBLE PRECISION NOT NULL,
            fuel_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_requests (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity DOUBLE PRECISION NOT NULL,
            proposed_price DOUBLE PRECISION NOT NULL,
            message TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_farmer_id
        ON products(farmer_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interests_buyer_id
        ON interests(buyer_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interests_product_id
        ON interests(product_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_purchase_requests_buyer
        ON purchase_requests(buyer_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_purchase_requests_farmer
        ON purchase_requests(farmer_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_purchase_requests_product
        ON purchase_requests(product_id)
    """)

    connection.commit()

    cursor.close()
    connection.close()

    print("PostgreSQL database created successfully!")


if __name__ == "__main__":
    create_database()
