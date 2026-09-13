from flask import Flask, jsonify, request, send_from_directory, send_file, session
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
import os
from openai import OpenAI

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "dev-secret-change-before-deployment"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"
)

CORS(app, supports_credentials=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))



openrouter_client = None


def get_openrouter_client():
    global openrouter_client

    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        return None

    if openrouter_client is None:
        openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": os.environ.get(
                    "APP_URL",
                    "https://your-service-name.onrender.com"
                ),
                "X-Title": "AgriConnect"
            },
            timeout=30.0
        )

    return openrouter_client


class DatabaseConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return self._connection.cursor(cursor_factory=RealDictCursor)

    def execute(self, query, params=()):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def get_database():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Please set the PostgreSQL connection URL."
        )
    return DatabaseConnection(psycopg2.connect(database_url))


def init_database():
    connection = get_database()
    cursor = connection.cursor()

    try:
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
                UNIQUE(buyer_id, product_id)
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

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_farmer_id ON products(farmer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interests_buyer_id ON interests(buyer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interests_product_id ON interests(product_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_requests_buyer ON purchase_requests(buyer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_requests_farmer ON purchase_requests(farmer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_requests_product ON purchase_requests(product_id)")

        connection.commit()
        print("PostgreSQL database initialized successfully!")
    finally:
        cursor.close()
        connection.close()


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    connection = get_database()

    user = connection.execute(
        """
        SELECT id, name, email, role, location
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return user


def require_login():
    user = get_current_user()

    if not user:
        return None, (
            jsonify({
                "error": "Authentication required"
            }),
            401
        )

    return user, None


def require_role(role):
    user, error = require_login()

    if error:
        return None, error

    if user["role"] != role:
        return None, (
            jsonify({
                "error": "You are not authorized to perform this action"
            }),
            403
        )

    return user, None


init_database()


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/createaccount.html")
def create_account_page():
    return send_from_directory(BASE_DIR, "createaccount.html")


@app.route("/login.html")
def login_page():
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/farmerdashboard.html")
def farmer_dashboard():
    return send_from_directory(BASE_DIR, "farmerdashboard.html")


@app.route("/consumerdashboard.html")
def consumer_dashboard():
    return send_from_directory(BASE_DIR, "consumerdashboard.html")


@app.route("/driverdashboard.html")
def driver_dashboard():
    return send_from_directory(BASE_DIR, "driverdashboard.html")


@app.route("/driver-dashboard.html")
def driver_dashboard_alt():
    return send_from_directory(BASE_DIR, "driverdashboard.html")


@app.route("/myinsurance.html")
def my_insurance_page():
    insurance_path = os.path.join(BASE_DIR, "myinsurance.html")

    if not os.path.isfile(insurance_path):
        return f"""
        <html>
        <body style="font-family:Arial;padding:40px">
        <h1>Insurance page file not found</h1>
        <p>Flask is looking for:</p>
        <pre>{insurance_path}</pre>
        </body>
        </html>
        """, 404

    return send_file(
        insurance_path,
        mimetype="text/html"
    )


@app.route("/vehicleregistration.html")
def vehicle_registration_page():
    return send_from_directory(
        BASE_DIR,
        "vehicleregistration.html"
    )


@app.route("/logo.png.jpeg")
def logo():
    return send_from_directory(
        BASE_DIR,
        "logo.png.jpeg"
    )


@app.route("/farmer.jpg")
def farmer_image():
    return send_from_directory(
        BASE_DIR,
        "farmer.jpg"
    )


@app.route("/crop.jpeg")
def crop_image():
    return send_from_directory(
        BASE_DIR,
        "crop.jpeg"
    )


@app.route("/weather.jpeg")
def weather_image():
    return send_from_directory(
        BASE_DIR,
        "weather.jpeg"
    )


@app.route("/plants.jpeg")
def plants_image():
    return send_from_directory(
        BASE_DIR,
        "plants.jpeg"
    )


@app.route("/coconut.jpeg")
def coconut_image():
    return send_from_directory(
        BASE_DIR,
        "coconut.jpeg"
    )


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
        ORDER BY products.id DESC
    """).fetchall()

    connection.close()

    return jsonify([
        dict(product)
        for product in products
    ])


@app.route("/products", methods=["POST"])
def add_product():
    farmer, error = require_role("farmer")

    if error:
        return error

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No product data provided"
        }), 400

    crop = str(
        data.get("crop", "")
    ).strip()

    quantity = data.get("quantity")
    price = data.get("price")

    location = str(
        data.get("location", "")
    ).strip()

    if (
        not crop
        or not location
        or quantity is None
        or price is None
    ):
        return jsonify({
            "error": "Crop, quantity, price and location are required"
        }), 400

    try:
        quantity = float(quantity)
        price = float(price)

    except (TypeError, ValueError):
        return jsonify({
            "error": "Quantity and price must be valid numbers"
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0"
        }), 400

    if price <= 0:
        return jsonify({
            "error": "Price must be greater than 0"
        }), 400

    connection = get_database()

    connection.execute(
        """
        INSERT INTO products
        (
            farmer_id,
            crop,
            quantity,
            price,
            location
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            farmer["id"],
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
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No user data provided"
        }), 400

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = data.get("password")

    role = str(
        data.get("role", "")
    ).strip().lower()

    location = str(
        data.get("location", "")
    ).strip()

    if (
        not name
        or not email
        or not password
        or not role
        or not location
    ):
        return jsonify({
            "error": "All fields are required"
        }), 400

    if role not in [
        "farmer",
        "buyer",
        "driver"
    ]:
        return jsonify({
            "error": "Role must be farmer, buyer or driver"
        }), 400

    if len(password) < 6:
        return jsonify({
            "error": "Password must be at least 6 characters long"
        }), 400

    connection = get_database()

    hashed_password = generate_password_hash(
        password
    )

    try:
        cursor = connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role,
                location
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                name,
                email,
                hashed_password,
                role,
                location
            )
        )

        user_id = cursor.fetchone()["id"]
        cursor.close()
        connection.commit()

    except psycopg2.IntegrityError:
        connection.close()

        return jsonify({
            "error": "Email already registered"
        }), 409

    connection.close()

    return jsonify({
        "message": "User created successfully!",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": role,
            "location": location
        }
    }), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No login data provided"
        }), 400

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    connection = get_database()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE email = %s
        """,
        (email,)
    ).fetchone()

    connection.close()

    if not user:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    try:
        password_valid = check_password_hash(
            user["password"],
            password
        )

    except Exception:
        password_valid = False

    if not password_valid:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    session.clear()

    session["user_id"] = user["id"]

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


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "message": "Logged out successfully"
    }), 200


@app.route("/me", methods=["GET"])
def me():
    user, error = require_login()

    if error:
        return error

    return jsonify(
        dict(user)
    ), 200


@app.route("/vehicles", methods=["POST"])
def register_vehicle():
    driver, error = require_role("driver")

    if error:
        return error

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No vehicle data provided"
        }), 400

    vehicle_type = str(
        data.get("vehicle_type", "")
    ).strip()

    vehicle_number = str(
        data.get("vehicle_number", "")
    ).strip().upper()

    capacity = data.get("capacity")

    fuel_type = str(
        data.get("fuel_type", "")
    ).strip()

    if (
        not vehicle_type
        or not vehicle_number
        or capacity is None
        or not fuel_type
    ):
        return jsonify({
            "error": "All vehicle fields are required"
        }), 400

    try:
        capacity = float(capacity)

    except (TypeError, ValueError):
        return jsonify({
            "error": "Capacity must be a valid number"
        }), 400

    if capacity <= 0:
        return jsonify({
            "error": "Capacity must be greater than 0"
        }), 400

    connection = get_database()

    existing_driver_vehicle = connection.execute(
        """
        SELECT id
        FROM vehicles
        WHERE driver_id = %s
        """,
        (driver["id"],)
    ).fetchone()

    if existing_driver_vehicle:

        try:
            connection.execute(
                """
                UPDATE vehicles
                SET
                    vehicle_type = %s,
                    vehicle_number = %s,
                    capacity = %s,
                    fuel_type = %s
                WHERE driver_id = %s
                """,
                (
                    vehicle_type,
                    vehicle_number,
                    capacity,
                    fuel_type,
                    driver["id"]
                )
            )

        except psycopg2.IntegrityError:
            connection.close()

            return jsonify({
                "error": "This vehicle registration number is already registered"
            }), 409

    else:

        try:
            connection.execute(
                """
                INSERT INTO vehicles
                (
                    driver_id,
                    vehicle_type,
                    vehicle_number,
                    capacity,
                    fuel_type
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    driver["id"],
                    vehicle_type,
                    vehicle_number,
                    capacity,
                    fuel_type
                )
            )

        except psycopg2.IntegrityError:
            connection.close()

            return jsonify({
                "error": "This vehicle registration number is already registered"
            }), 409

    connection.commit()

    vehicle = connection.execute(
        """
        SELECT
            id,
            driver_id,
            vehicle_type,
            vehicle_number,
            capacity,
            fuel_type,
            created_at
        FROM vehicles
        WHERE driver_id = %s
        """,
        (driver["id"],)
    ).fetchone()

    connection.close()

    return jsonify({
        "message": "Vehicle registered successfully!",
        "vehicle": dict(vehicle)
    }), 201


@app.route("/vehicles/<int:driver_id>", methods=["GET"])
def get_vehicle(driver_id):
    driver, error = require_role("driver")

    if error:
        return error

    if driver["id"] != driver_id:
        return jsonify({
            "error": "You are not authorized to view this vehicle"
        }), 403

    connection = get_database()

    vehicle = connection.execute(
        """
        SELECT
            id,
            driver_id,
            vehicle_type,
            vehicle_number,
            capacity,
            fuel_type,
            created_at
        FROM vehicles
        WHERE driver_id = %s
        """,
        (driver_id,)
    ).fetchone()

    connection.close()

    if not vehicle:
        return jsonify({
            "error": "Vehicle not registered"
        }), 404

    return jsonify(
        dict(vehicle)
    ), 200


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
            LIKE LOWER(%s)
        """

        parameters.append(
            f"%{crop.strip()}%"
        )

    if location:
        query += """
            AND LOWER(products.location)
            LIKE LOWER(%s)
        """

        parameters.append(
            f"%{location.strip()}%"
        )

    min_price_value = None
    max_price_value = None

    if min_price:

        try:
            min_price_value = float(
                min_price
            )

        except ValueError:
            connection.close()

            return jsonify({
                "error": "Minimum price must be a number"
            }), 400

        if min_price_value < 0:
            connection.close()

            return jsonify({
                "error": "Minimum price cannot be negative"
            }), 400

        query += """
            AND products.price >= %s
        """

        parameters.append(
            min_price_value
        )

    if max_price:

        try:
            max_price_value = float(
                max_price
            )

        except ValueError:
            connection.close()

            return jsonify({
                "error": "Maximum price must be a number"
            }), 400

        if max_price_value < 0:
            connection.close()

            return jsonify({
                "error": "Maximum price cannot be negative"
            }), 400

        query += """
            AND products.price <= %s
        """

        parameters.append(
            max_price_value
        )

    if (
        min_price_value is not None
        and max_price_value is not None
        and min_price_value > max_price_value
    ):
        connection.close()

        return jsonify({
            "error": "Minimum price cannot be greater than maximum price"
        }), 400

    query += """
        ORDER BY products.id DESC
    """

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
    buyer, error = require_role("buyer")

    if error:
        return error

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No interest data provided"
        }), 400

    product_id = data.get("product_id")

    if product_id is None:
        return jsonify({
            "error": "Product ID is required"
        }), 400

    try:
        product_id = int(
            product_id
        )

    except (TypeError, ValueError):
        return jsonify({
            "error": "Product ID must be a valid number"
        }), 400

    connection = get_database()

    product = connection.execute(
        """
        SELECT *
        FROM products
        WHERE id = %s
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
            (
                buyer_id,
                product_id
            )
            VALUES (%s, %s)
            """,
            (
                buyer["id"],
                product_id
            )
        )

        connection.commit()

    except psycopg2.IntegrityError:
        connection.close()

        return jsonify({
            "error": "You have already shown interest in this product"
        }), 409

    connection.close()

    return jsonify({
        "message": "Interest recorded successfully!"
    }), 201


@app.route("/interests", methods=["GET"])
def get_interests():
    farmer, error = require_role("farmer")

    if error:
        return error

    connection = get_database()

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
        WHERE products.farmer_id = %s
        ORDER BY interests.id DESC
        """,
        (farmer["id"],)
    ).fetchall()

    connection.close()

    return jsonify([
        dict(interest)
        for interest in interests
    ]), 200



@app.route("/purchase-requests", methods=["POST"])
def create_purchase_request():
    buyer, error = require_role("buyer")

    if error:
        return error

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No purchase request data provided"
        }), 400

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    proposed_price = data.get("proposed_price")
    message = str(data.get("message", "")).strip()

    if product_id is None or quantity is None or proposed_price is None:
        return jsonify({
            "error": "Product, quantity and proposed price are required"
        }), 400

    try:
        product_id = int(product_id)
        quantity = float(quantity)
        proposed_price = float(proposed_price)
    except (TypeError, ValueError):
        return jsonify({
            "error": "Product ID, quantity and proposed price must be valid numbers"
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0"
        }), 400

    if proposed_price <= 0:
        return jsonify({
            "error": "Proposed price must be greater than 0"
        }), 400

    if len(message) > 1000:
        return jsonify({
            "error": "Message cannot exceed 1000 characters"
        }), 400

    connection = get_database()

    product = connection.execute(
        """
        SELECT
            id,
            farmer_id,
            crop,
            quantity,
            price,
            location
        FROM products
        WHERE id = %s
        """,
        (product_id,)
    ).fetchone()

    if not product:
        connection.close()
        return jsonify({
            "error": "Product not found"
        }), 404

    if not product["farmer_id"]:
        connection.close()
        return jsonify({
            "error": "This product is not linked to a farmer"
        }), 400

    if product["farmer_id"] == buyer["id"]:
        connection.close()
        return jsonify({
            "error": "You cannot request your own product"
        }), 400

    if quantity > float(product["quantity"]):
        connection.close()
        return jsonify({
            "error": "Requested quantity exceeds available quantity"
        }), 400

    existing = connection.execute(
        """
        SELECT id
        FROM purchase_requests
        WHERE buyer_id = %s
          AND product_id = %s
          AND status = 'pending'
        """,
        (buyer["id"], product_id)
    ).fetchone()

    if existing:
        connection.close()
        return jsonify({
            "error": "You already have a pending request for this product"
        }), 409

    cursor = connection.execute(
        """
        INSERT INTO purchase_requests
        (
            buyer_id,
            farmer_id,
            product_id,
            quantity,
            proposed_price,
            message,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        RETURNING id
        """,
        (
            buyer["id"],
            product["farmer_id"],
            product_id,
            quantity,
            proposed_price,
            message
        )
    )

    request_id = cursor.fetchone()["id"]
    cursor.close()
    connection.commit()
    connection.close()

    return jsonify({
        "message": "Purchase request sent successfully!",
        "request_id": request_id
    }), 201


@app.route("/purchase-requests", methods=["GET"])
def get_purchase_requests():
    user, error = require_login()

    if error:
        return error

    connection = get_database()

    if user["role"] == "buyer":
        requests = connection.execute(
            """
            SELECT
                purchase_requests.id AS request_id,
                purchase_requests.product_id,
                purchase_requests.farmer_id,
                users.name AS farmer_name,
                users.email AS farmer_email,
                users.location AS farmer_location,
                products.crop,
                products.location AS product_location,
                purchase_requests.quantity,
                purchase_requests.proposed_price,
                purchase_requests.message,
                purchase_requests.status,
                purchase_requests.created_at,
                purchase_requests.updated_at
            FROM purchase_requests
            INNER JOIN users
            ON purchase_requests.farmer_id = users.id
            INNER JOIN products
            ON purchase_requests.product_id = products.id
            WHERE purchase_requests.buyer_id = %s
            ORDER BY purchase_requests.id DESC
            """,
            (user["id"],)
        ).fetchall()

    elif user["role"] == "farmer":
        requests = connection.execute(
            """
            SELECT
                purchase_requests.id AS request_id,
                purchase_requests.product_id,
                purchase_requests.buyer_id,
                users.name AS buyer_name,
                users.email AS buyer_email,
                users.location AS buyer_location,
                products.crop,
                products.location AS product_location,
                products.quantity AS available_quantity,
                products.price AS listed_price,
                purchase_requests.quantity,
                purchase_requests.proposed_price,
                purchase_requests.message,
                purchase_requests.status,
                purchase_requests.created_at,
                purchase_requests.updated_at
            FROM purchase_requests
            INNER JOIN users
            ON purchase_requests.buyer_id = users.id
            INNER JOIN products
            ON purchase_requests.product_id = products.id
            WHERE purchase_requests.farmer_id = %s
            ORDER BY purchase_requests.id DESC
            """,
            (user["id"],)
        ).fetchall()

    else:
        connection.close()
        return jsonify({
            "error": "Only buyers and farmers can view purchase requests"
        }), 403

    connection.close()

    return jsonify([
        dict(item)
        for item in requests
    ]), 200


@app.route("/purchase-requests/<int:request_id>", methods=["PATCH"])
def update_purchase_request(request_id):
    farmer, error = require_role("farmer")

    if error:
        return error

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No update data provided"
        }), 400

    status = str(
        data.get("status", "")
    ).strip().lower()

    if status not in ["accepted", "rejected"]:
        return jsonify({
            "error": "Status must be accepted or rejected"
        }), 400

    connection = get_database()

    purchase_request = connection.execute(
        """
        SELECT
            purchase_requests.id,
            purchase_requests.product_id,
            purchase_requests.quantity,
            purchase_requests.status,
            products.quantity AS available_quantity
        FROM purchase_requests
        INNER JOIN products
        ON purchase_requests.product_id = products.id
        WHERE purchase_requests.id = %s
          AND purchase_requests.farmer_id = %s
        """,
        (request_id, farmer["id"])
    ).fetchone()

    if not purchase_request:
        connection.close()
        return jsonify({
            "error": "Purchase request not found"
        }), 404

    if purchase_request["status"] != "pending":
        connection.close()
        return jsonify({
            "error": "This purchase request has already been processed"
        }), 409

    if status == "accepted":
        if float(purchase_request["quantity"]) > float(
            purchase_request["available_quantity"]
        ):
            connection.close()
            return jsonify({
                "error": "Requested quantity is no longer available"
            }), 409

        quantity_cursor = connection.execute(
            """
            UPDATE products
            SET quantity = quantity - %s
            WHERE id = %s
              AND quantity >= %s
            """,
            (
                purchase_request["quantity"],
                purchase_request["product_id"],
                purchase_request["quantity"]
            )
        )

        if quantity_cursor.rowcount == 0:
            quantity_cursor.close()
            connection.rollback()
            connection.close()
            return jsonify({
                "error": "Requested quantity is no longer available"
            }), 409

        quantity_cursor.close()

    connection.execute(
        """
        UPDATE purchase_requests
        SET
            status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (status, request_id)
    )

    connection.commit()

    updated = connection.execute(
        """
        SELECT
            id AS request_id,
            status,
            updated_at
        FROM purchase_requests
        WHERE id = %s
        """,
        (request_id,)
    ).fetchone()

    connection.close()

    return jsonify({
        "message": (
            "Purchase request accepted!"
            if status == "accepted"
            else "Purchase request rejected."
        ),
        "request": dict(updated)
    }), 200


@app.route("/chat", methods=["POST"])
def chat():
    user = get_current_user()

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No chat data provided"
        }), 400

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "error": "Message is required"
        }), 400

    if user:
        role = user["role"]
    else:
        role = str(
            data.get("role", "")
        ).strip().lower()

    if role == "farmer":

        system_prompt = (
            "You are AgriConnect AI, an assistant for farmers using the "
            "AgriConnect agricultural marketplace. Help with farming, crops, "
            "selling agricultural products, crop insurance, and using the "
            "AgriConnect platform. Give clear, practical answers."
        )

    elif role == "buyer":

        system_prompt = (
            "You are AgriConnect AI, an assistant for buyers using the "
            "AgriConnect agricultural marketplace. Help with buying agricultural "
            "products, finding products, and using the platform. "
            "Give clear, practical answers."
        )

    elif role == "driver":

        system_prompt = (
            "You are AgriConnect AI, an assistant for delivery drivers using "
            "the AgriConnect agricultural marketplace. Help with deliveries, "
            "transporting agricultural products, vehicle information, and using "
            "the platform. Give clear, practical answers."
        )

    else:

        system_prompt = (
            "You are AgriConnect AI, a helpful assistant for the AgriConnect "
            "agricultural marketplace. Answer questions clearly and help users "
            "understand and use the platform."
        )

    client = get_openrouter_client()
    if client is None:
        return jsonify({
            "error": "AI service is not configured"
        }), 503

     try:
        response = client.chat.completions.create(
            model=os.environ.get(
                "OPENROUTER_MODEL",
                "openai/gpt-4o-mini"
            ),
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.7,
            max_tokens=500
        )

        if not response.choices:
            return jsonify({
                "error": "The AI returned no choices"
            }), 502

        reply = response.choices[0].message.content

        if not reply:
            return jsonify({
                "error": "The AI returned an empty response"
            }), 502

        return jsonify({
            "reply": reply
        }), 200

    except Exception:
        app.logger.exception("OpenRouter request failed")

        return jsonify({
            "error": "Unable to get a response from the AI assistant"
        }), 502

    reply = response.choices[0].message.content

    if not reply:
        return jsonify({
            "error": "The AI returned an empty response"
        }), 502

    return jsonify({
        "reply": reply
    }), 200

except Exception as error:
    app.logger.exception("OpenRouter request failed")

    return jsonify({
        "error": "Unable to get a response from the AI assistant"
    }), 502

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok"
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
