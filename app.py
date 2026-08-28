from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
CORS(app)


def get_database():
    connection = sqlite3.connect("agriconnect.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/createaccount.html")
def create_account_page():
    return send_from_directory(".", "createaccount.html")


@app.route("/login.html")
def login_page():
    return send_from_directory(".", "login.html")


@app.route("/farmerdashboard.html")
def farmer_dashboard():
    return send_from_directory(".", "farmerdashboard.html")


@app.route("/consumerdashboard.html")
def consumer_dashboard():
    return send_from_directory(".", "consumerdashboard.html")


@app.route("/logo.png.jpeg")
def logo():
    return send_from_directory(".", "logo.png.jpeg")


@app.route("/products", methods=["GET"])
def get_products():

    connection = get_database()

    products = connection.execute("""
        SELECT
            products.id,
            products.crop,
            products.quantity,
            products.price,
            products.location,
            products.farmer_id,
            users.name AS farmer_name,
            users.location AS farmer_location
        FROM products
        LEFT JOIN users
        ON products.farmer_id = users.id
    """).fetchall()

    connection.close()

    return jsonify([
        dict(product)
        for product in products
    ])


@app.route("/products", methods=["POST"])
def add_product():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No product data provided"
        }), 400

    farmer_id = data.get("farmer_id")
    crop = data.get("crop")
    quantity = data.get("quantity")
    price = data.get("price")
    location = data.get("location")

    if farmer_id is None:
        return jsonify({
            "error": "Farmer ID is required"
        }), 400

    if not crop or not location:
        return jsonify({
            "error": "Crop and location are required"
        }), 400

    if quantity is None or quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0"
        }), 400

    if price is None or price <= 0:
        return jsonify({
            "error": "Price must be greater than 0"
        }), 400

    connection = get_database()

    farmer = connection.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'farmer'",
        (farmer_id,)
    ).fetchone()

    if not farmer:
        connection.close()

        return jsonify({
            "error": "Farmer not found"
        }), 404

    connection.execute(
        """
        INSERT INTO products
        (farmer_id, crop, quantity, price, location)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            farmer_id,
            crop,
            quantity,
            price,
            location
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Product added successfully!"
    }), 201


@app.route("/users", methods=["POST"])
def add_user():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No user data provided"
        }), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    location = data.get("location")

    if not name or not email or not password or not role or not location:
        return jsonify({
            "error": "All fields are required"
        }), 400

    if role not in ["farmer", "buyer"]:
        return jsonify({
            "error": "Role must be farmer or buyer"
        }), 400

    connection = get_database()

    hashed_password = generate_password_hash(password)

    try:

        connection.execute(
            """
            INSERT INTO users
            (name, email, password, role, location)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password,
                role,
                location
            )
        )

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        return jsonify({
            "error": "Email already registered"
        }), 409

    connection.close()

    return jsonify({
        "message": "User created successfully!"
    }), 201


@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No login data provided"
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    connection = get_database()

    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    connection.close()

    if not user:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    if not check_password_hash(
        user["password"],
        password
    ):
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    return jsonify({
        "message": "Login successful!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "location": user["location"]
        }
    }), 200


@app.route("/search", methods=["GET"])
def search_products():

    crop = request.args.get("crop")
    location = request.args.get("location")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    connection = get_database()

    query = """
        SELECT
            products.id,
            products.crop,
            products.quantity,
            products.price,
            products.location,
            products.farmer_id,
            users.name AS farmer_name,
            users.location AS farmer_location
        FROM products
        LEFT JOIN users
        ON products.farmer_id = users.id
        WHERE 1=1
    """

    parameters = []

    if crop:

        query += """
            AND LOWER(products.crop)
            LIKE LOWER(?)
        """

        parameters.append(
            f"%{crop}%"
        )

    if location:

        query += """
            AND LOWER(products.location)
            LIKE LOWER(?)
        """

        parameters.append(
            f"%{location}%"
        )

    if min_price:

        try:

            min_price_value = float(
                min_price
            )

            if min_price_value < 0:

                connection.close()

                return jsonify({
                    "error":
                    "Minimum price cannot be negative"
                }), 400

            query += """
                AND products.price >= ?
            """

            parameters.append(
                min_price_value
            )

        except ValueError:

            connection.close()

            return jsonify({
                "error":
                "Minimum price must be a number"
            }), 400

    if max_price:

        try:

            max_price_value = float(
                max_price
            )

            if max_price_value < 0:

                connection.close()

                return jsonify({
                    "error":
                    "Maximum price cannot be negative"
                }), 400

            query += """
                AND products.price <= ?
            """

            parameters.append(
                max_price_value
            )

        except ValueError:

            connection.close()

            return jsonify({
                "error":
                "Maximum price must be a number"
            }), 400

    if min_price and max_price:

        try:

            if float(min_price) > float(max_price):

                connection.close()

                return jsonify({
                    "error":
                    "Minimum price cannot be greater than maximum price"
                }), 400

        except ValueError:

            connection.close()

            return jsonify({
                "error":
                "Invalid price values"
            }), 400

    products = connection.execute(
        query,
        parameters
    ).fetchall()

    connection.close()

    return jsonify([
        dict(product)
        for product in products
    ])


@app.route("/interests", methods=["POST"])
def add_interest():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No interest data provided"
        }), 400

    buyer_id = data.get("buyer_id")
    product_id = data.get("product_id")

    if buyer_id is None or product_id is None:
        return jsonify({
            "error":
            "Buyer ID and product ID are required"
        }), 400

    connection = get_database()

    buyer = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        AND role = 'buyer'
        """,
        (buyer_id,)
    ).fetchone()

    if not buyer:

        connection.close()

        return jsonify({
            "error": "Buyer not found"
        }), 404

    product = connection.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    if not product:

        connection.close()

        return jsonify({
            "error": "Product not found"
        }), 404

    try:

        connection.execute(
            """
            INSERT INTO interests
            (buyer_id, product_id)
            VALUES (?, ?)
            """,
            (
                buyer_id,
                product_id
            )
        )

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        return jsonify({
            "error":
            "You have already shown interest in this product"
        }), 409

    connection.close()

    return jsonify({
        "message":
        "Interest recorded successfully!"
    }), 201


@app.route("/interests", methods=["GET"])
def get_interests():

    farmer_id = request.args.get("farmer_id")

    if farmer_id is None:
        return jsonify({
            "error": "Farmer ID is required"
        }), 400

    try:
        farmer_id = int(farmer_id)

    except ValueError:
        return jsonify({
            "error": "Invalid farmer ID"
        }), 400

    connection = get_database()

    farmer = connection.execute(
        """
        SELECT id
        FROM users
        WHERE id = ?
        AND role = 'farmer'
        """,
        (farmer_id,)
    ).fetchone()

    if not farmer:

        connection.close()

        return jsonify({
            "error": "Farmer not found"
        }), 404

    interests = connection.execute(
        """
        SELECT
            interests.id AS interest_id,

            users.id AS buyer_id,
            users.name AS buyer_name,
            users.email AS buyer_email,
            users.location AS buyer_location,

            products.id AS product_id,
            products.crop AS product_crop,
            products.quantity AS product_quantity,
            products.price AS product_price,
            products.location AS product_location,

            interests.created_at AS created_at

        FROM interests

        INNER JOIN users
        ON interests.buyer_id = users.id

        INNER JOIN products
        ON interests.product_id = products.id

        WHERE products.farmer_id = ?

        ORDER BY interests.id DESC
        """,
        (farmer_id,)
    ).fetchall()

    connection.close()

    return jsonify([
        dict(interest)
        for interest in interests
    ]), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
