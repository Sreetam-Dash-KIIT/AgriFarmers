```python
import sqlite3


connection = sqlite3.connect("agriconnect.db")
cursor = connection.cursor()


# Users table
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


# Products table
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


# Add farmer_id to existing products table if it doesn't exist
try:
    cursor.execute(
        "ALTER TABLE products ADD COLUMN farmer_id INTEGER"
    )
except sqlite3.OperationalError:
    pass


# Buyer interests table
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


connection.commit()
connection.close()


print("Database tables updated successfully!")
```

