from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
import mysql.connector
from mysql.connector import IntegrityError
from datetime import timedelta, date
import json
import os
from datetime import datetime

mydb = None
my_cursor = None

app = Flask(__name__)
app.secret_key = "hello"

def init_db():
    global mydb, my_cursor
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='1234.'
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS storefront")
        conn.close()

        mydb = mysql.connector.connect(
            host='localhost',
            user='root',
            password='1234.',
            database='storefront'
        )
        my_cursor = mydb.cursor()

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS User (
                user_id INT PRIMARY KEY AUTO_INCREMENT,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(50) NOT NULL,
                city VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Address (
                address_id INT PRIMARY KEY AUTO_INCREMENT,
                street_address VARCHAR(255) NOT NULL,
                city VARCHAR(100) NOT NULL,
                state VARCHAR(50) NOT NULL,
                postal_code VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Warehouse (
                warehouse_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                address_id INT NOT NULL,
                capacity INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (address_id) REFERENCES Address(address_id)
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Manager (
                manager_id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                warehouse_id INT,
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES User(user_id),
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Employee (
                employee_id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                warehouse_id INT NOT NULL,
                phone_number VARCHAR(20),
                position VARCHAR(50),
                salary DECIMAL(10,2),
                hire_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES User(user_id),
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
            )
        """)

        try:
            my_cursor.execute("SHOW COLUMNS FROM Employee LIKE 'phone_number'")
            if not my_cursor.fetchone():
                my_cursor.execute("ALTER TABLE Employee ADD COLUMN phone_number VARCHAR(20) AFTER warehouse_id")

            my_cursor.execute("SHOW COLUMNS FROM Employee LIKE 'position'")
            if not my_cursor.fetchone():
                my_cursor.execute("ALTER TABLE Employee ADD COLUMN position VARCHAR(50) AFTER phone_number")

            my_cursor.execute("SHOW COLUMNS FROM Employee LIKE 'salary'")
            if not my_cursor.fetchone():
                my_cursor.execute("ALTER TABLE Employee ADD COLUMN salary DECIMAL(10,2) AFTER position")

            my_cursor.execute("SHOW COLUMNS FROM Employee LIKE 'hire_date'")
            if not my_cursor.fetchone():
                my_cursor.execute("ALTER TABLE Employee ADD COLUMN hire_date DATE AFTER salary")

            # Check if warehouse_id column exists
            my_cursor.execute("SHOW COLUMNS FROM Employee LIKE 'warehouse_id'")
            if not my_cursor.fetchone():
                # First get a default warehouse
                my_cursor.execute("SELECT warehouse_id FROM Warehouse LIMIT 1")
                default_warehouse = my_cursor.fetchone()
                if default_warehouse:
                    default_warehouse_id = default_warehouse[0]
                    # Add warehouse_id column
                    my_cursor.execute("ALTER TABLE Employee ADD COLUMN warehouse_id INT AFTER user_id")
                    # Add foreign key constraint
                    my_cursor.execute("""
                        ALTER TABLE Employee 
                        ADD CONSTRAINT fk_employee_warehouse 
                        FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
                    """)
                    # Update existing employees with default warehouse
                    my_cursor.execute("UPDATE Employee SET warehouse_id = %s WHERE warehouse_id IS NULL", (default_warehouse_id,))
        except Exception as e:
            if "Duplicate column name" not in str(e):
                raise e

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Customer (
                customer_id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES User(user_id)
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Branch (
                branch_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                address_id INT NOT NULL,
                primary_warehouse_id INT,
                secondary_warehouse_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (address_id) REFERENCES Address(address_id),
                FOREIGN KEY (primary_warehouse_id) REFERENCES Warehouse(warehouse_id),
                FOREIGN KEY (secondary_warehouse_id) REFERENCES Warehouse(warehouse_id)
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Product (
                product_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                cost_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                category VARCHAR(50),
                description TEXT,
                img_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            my_cursor.execute("""
                ALTER TABLE Product 
                ADD COLUMN cost_price DECIMAL(10,2) NOT NULL DEFAULT 0.00 
                AFTER price
            """)
        except Exception as e:
            if "Duplicate column name" not in str(e):
                raise e

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Product_Warehouse (
                product_id INT NOT NULL,
                warehouse_id INT NOT NULL,
                quantity_in_stock INT NOT NULL DEFAULT 0,
                minimum_stock INT NOT NULL DEFAULT 0,
                maximum_stock INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_id, warehouse_id),
                FOREIGN KEY (product_id) REFERENCES Product(product_id),
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Supplier (
                supplier_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(20),
                address_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (address_id) REFERENCES Address(address_id)
            )
        """)

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Purchase_Order (
                purchase_order_id INT PRIMARY KEY AUTO_INCREMENT,
                warehouse_id INT NOT NULL,
                supplier_id INT NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expected_delivery_date TIMESTAMP,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id),
                FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id)
            )
        """)

        try:
            my_cursor.execute("""
                ALTER TABLE Purchase_order 
                CHANGE COLUMN delivery_date expected_delivery_date TIMESTAMP
            """)
        except Exception as e:
            pass

        my_cursor.execute("""
            CREATE TABLE IF NOT EXISTS Purchase_Order_Details (
                purchase_order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (purchase_order_id, product_id),
                FOREIGN KEY (purchase_order_id) REFERENCES Purchase_Order(purchase_order_id),
                FOREIGN KEY (product_id) REFERENCES Product(product_id)
            )
        """)

        mydb.commit()

        my_cursor.execute("SELECT COUNT(*) FROM Warehouse")
        warehouse_count = my_cursor.fetchone()[0]

        if warehouse_count == 0:
            palestinian_cities = [
                {'name': 'Gaza City Warehouse', 'street': 'Al-Rasheed Street', 'city': 'Gaza City', 'state': 'Gaza Strip', 'postal_code': '00972', 'capacity': 5000},
                {'name': 'Ramallah Distribution Center', 'street': 'Al-Irsal Street', 'city': 'Ramallah', 'state': 'West Bank', 'postal_code': '00970', 'capacity': 4000},
                {'name': 'Hebron Storage Facility', 'street': 'Al-Shuhada Street', 'city': 'Hebron', 'state': 'West Bank', 'postal_code': '00970', 'capacity': 3500},
                {'name': 'Nablus Warehouse', 'street': 'Al-Nasr Street', 'city': 'Nablus', 'state': 'West Bank', 'postal_code': '00970', 'capacity': 3000},
                {'name': 'Bethlehem Logistics Center', 'street': 'Manger Street', 'city': 'Bethlehem', 'state': 'West Bank', 'postal_code': '00970', 'capacity': 2500},
                {'name': 'Jericho Storage Facility', 'street': 'Al-Sultan Street', 'city': 'Jericho', 'state': 'West Bank', 'postal_code': '00970', 'capacity': 2000},
                {'name': 'Khan Yunis Warehouse', 'street': 'Al-Amal Street', 'city': 'Khan Yunis', 'state': 'Gaza Strip', 'postal_code': '00972', 'capacity': 2800},
                {'name': 'Rafah Distribution Center', 'street': 'Al-Nasser Street', 'city': 'Rafah', 'state': 'Gaza Strip', 'postal_code': '00972', 'capacity': 2200}
            ]

            for city_data in palestinian_cities:
                my_cursor.execute("""
                    INSERT INTO Address (street_address, city, state, postal_code)
                    VALUES (%s, %s, %s, %s)
                """, (
                    city_data['street'],
                    city_data['city'],
                    city_data['state'],
                    city_data['postal_code']
                ))
                address_id = my_cursor.lastrowid

                my_cursor.execute("""
                    INSERT INTO Warehouse (name, address_id, capacity)
                    VALUES (%s, %s, %s)
                """, (
                    city_data['name'],
                    address_id,
                    city_data['capacity']
                ))

            mydb.commit()
    except Exception as e:
        raise e

def get_db_connection():
    global mydb, my_cursor
    try:
        if mydb is None or not mydb.is_connected():
            if my_cursor is not None:
                try:
                    my_cursor.close()
                except:
                    pass
            if mydb is not None:
                try:
                    mydb.close()
                except:
                    pass

            mydb = mysql.connector.connect(
                host='localhost',
                user='root',
                password='1234',
                database='storefront'
            )
            my_cursor = mydb.cursor()
        return mydb, my_cursor
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise e


@app.route('/')
def index():
    try:
        my_cursor.execute("""
            SELECT p.*, 
                MAX(pb.quantity_in_stock) as quantity_in_stock, 
                MAX(s.name) as supplier_name
            FROM Product p
            LEFT JOIN Product_Branch pb ON p.product_id = pb.product_id
            LEFT JOIN Purchase_Order_Details pod ON p.product_id = pod.product_id
            LEFT JOIN Purchase_order po ON pod.purchase_order_id = po.purchase_order_id
            LEFT JOIN Supplier s ON po.supplier_id = s.supplier_id
            GROUP BY p.product_id
            ORDER BY p.product_id DESC
        """)
        products = my_cursor.fetchall()

        product_list = []
        for product in products:
            product_dict = {
                "product_id": product[0],
                "name": product[1],
                "price": float(product[2]),
                "category": product[3],
                "description": product[4],
                "stock_quantity": product[5] if product[5] is not None else 0,
                "supplier_name": product[6] if product[6] is not None else "No supplier"
            }
            product_list.append(product_dict)

        return render_template('index.html', products=product_list)
    except Exception:
        flash("Error loading products", "error")
        return render_template('index.html', products=[])


@app.route('/api/categories')
def get_categories():
    try:
        my_cursor.execute("""
            SELECT DISTINCT category 
            FROM Product 
            WHERE category IS NOT NULL
            ORDER BY category
        """)
        categories = my_cursor.fetchall()
        return jsonify([cat[0] for cat in categories if cat[0]])
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/products/category/<category>')
def get_products_by_category(category):
    try:
        my_cursor.execute("""
            SELECT p.*, 
                MAX(pb.quantity_in_stock) as quantity_in_stock, 
                MAX(s.name) as supplier_name
            FROM Product p
            LEFT JOIN Product_Branch pb ON p.product_id = pb.product_id
            LEFT JOIN Purchase_Order_Details pod ON p.product_id = pod.product_id
            LEFT JOIN Purchase_order po ON pod.purchase_order_id = po.purchase_order_id
            LEFT JOIN Supplier s ON po.supplier_id = s.supplier_id
            WHERE p.category = %s
            GROUP BY p.product_id
        """, (category,))

        products = my_cursor.fetchall()

        product_list = []
        for product in products:
            product_dict = {
                "product_id": product[0],
                "name": product[1],
                "price": float(product[2]),
                "category": product[3],
                "description": product[4],
                "stock_quantity": product[5] if product[5] is not None else 0,
                "supplier_name": product[6] if product[6] is not None else "No supplier"
            }
            product_list.append(product_dict)

        return jsonify(product_list)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/products/search')
def search_products():
    query = request.args.get('q', '')
    try:
        my_cursor.execute("""
            SELECT p.*, 
                MAX(pb.quantity_in_stock) as quantity_in_stock, 
                MAX(s.name) as supplier_name
            FROM Product p
            LEFT JOIN Product_Branch pb ON p.product_id = pb.product_id
            LEFT JOIN Purchase_Order_Details pod ON p.product_id = pod.product_id
            LEFT JOIN Purchase_order po ON pod.purchase_order_id = po.purchase_order_id
            LEFT JOIN Supplier s ON po.supplier_id = s.supplier_id
            WHERE p.name LIKE %s 
            OR p.description LIKE %s 
            OR p.category LIKE %s
            GROUP BY p.product_id
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))

        products = my_cursor.fetchall()

        product_list = []
        for product in products:
            product_dict = {
                "product_id": product[0],
                "name": product[1],
                "price": float(product[2]),
                "category": product[3],
                "description": product[4],
                "img_path": product[6],   # <---- this is important!
                "stock_quantity": product[5] if product[5] is not None else 0,
                "supplier_name": product[6] if product[6] is not None else "No supplier"
            }

            product_list.append(product_dict)

        return jsonify(product_list)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/product/<int:product_id>')
def product_details(product_id):
    try:
        my_cursor.execute("""
            SELECT 
                p.product_id, p.name, p.price, p.cost_price, p.category, p.description, p.img_path, p.created_at,
                s.name AS supplier_name, s.phone_number AS supplier_phone,
                a.street_address, a.city, a.state, a.postal_code, a.country
            FROM Product p
            LEFT JOIN Purchase_Order_Details pod ON p.product_id = pod.product_id
            LEFT JOIN Purchase_order po ON pod.purchase_order_id = po.purchase_order_id
            LEFT JOIN Supplier s ON po.supplier_id = s.supplier_id
            LEFT JOIN Address a ON s.address_id = a.address_id
            WHERE p.product_id = %s
            LIMIT 1
        """, (product_id,))
        row = my_cursor.fetchone()

        if not row:
            flash("Product not found", "error")
            return redirect(url_for('index'))

        product_data = {
            "product_id": row[0],
            "name": row[1],
            "price": float(row[2]),
            "cost_price": float(row[3]),
            "category": row[4],
            "description": row[5],
            "img_path": row[6],
            "created_at": str(row[7]),
            "supplier": {
                "name": row[8] or "No supplier",
                "phone": row[9] or "N/A",
                "address": {
                    "street": row[10] or "N/A",
                    "city": row[11] or "N/A",
                    "state": row[12] or "N/A",
                    "postal_code": row[13] or "N/A",
                    "country": row[14] or "N/A"
                }
            }
        }

        my_cursor.execute("""
            SELECT b.name as branch_name, a.city, a.state, a.street_address, pb.quantity_in_stock
            FROM Product_Branch pb
            JOIN Branch b ON pb.branch_id = b.branch_id
            JOIN Address a ON b.address_id = a.address_id
            WHERE pb.product_id = %s
        """, (product_id,))
        availability = []
        for b in my_cursor.fetchall():
            availability.append({
                "branch_name": b[0],
                "location": f"{b[3]}, {b[1]}, {b[2]}",
                "quantity": b[4]
            })
        product_data['availability'] = availability

        return render_template('product_details.html', product=product_data)
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            mydb, my_cursor = get_db_connection()
            login_query = """
                SELECT 
                    u.user_id, 
                    u.email, 
                    u.password, 
                    u.name, 
                    LOWER(u.role) as role, 
                    u.created_at,
                    CASE 
                        WHEN u.role = 'MANAGER' THEN m.manager_id
                        WHEN u.role = 'EMPLOYEE' THEN e.employee_id
                        WHEN u.role = 'CUSTOMER' THEN c.customer_id
                        ELSE NULL
                    END as role_id,
                    u.role as original_role
                FROM User u
                LEFT JOIN Manager m ON u.user_id = m.user_id
                LEFT JOIN Employee e ON u.user_id = e.user_id
                LEFT JOIN Customer c ON u.user_id = c.user_id
                WHERE u.email = %s
            """
            my_cursor.execute(login_query, (email,))
            user = my_cursor.fetchone()

            if user and user[2] == password:
                session.clear()
                session['user_id'] = user[0]
                session['email'] = user[1]
                session['name'] = user[3]
                session['role'] = user[4]
                session['role_id'] = user[6]
                flash('Login successful!', 'success')

                if user[4] == 'customer':
                    return redirect(url_for('customer_dashboard'))
                elif user[4] == 'owner':
                    return redirect(url_for('owner_dashboard'))
                elif user[4] == 'manager':
                    return redirect(url_for('manager_dashboard'))
                elif user[4] == 'employee':
                    return redirect(url_for('employee_dashboard'))
                else:
                    flash('Invalid role', 'error')
                    return redirect(url_for('login'))
            else:
                flash('Invalid email or password', 'error')
                return redirect(url_for('login'))

        except mysql.connector.Error:
            flash('Database error. Please try again.', 'error')
            return redirect(url_for('login'))

        except Exception:
            flash('An error occurred during login. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')
@app.route('/api/warehouses')
def get_warehouses():
    try:
        my_cursor.execute("""
            SELECT w.warehouse_id, w.name, 
                   CONCAT(a.street_address, ', ', a.city, ', ', a.state, ' ', a.postal_code) as full_address
            FROM Warehouse w
            JOIN Address a ON w.address_id = a.address_id
            ORDER BY w.name
        """)
        warehouses = my_cursor.fetchall()
        return jsonify([{
            'id': w[0],
            'name': w[1],
            'address': w[2]
        } for w in warehouses])
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/manager-dashboard')
def manager_dashboard():
    if 'user_id' not in session or session.get('role') != 'manager':
        flash('Access denied. Please login as a manager.', 'error')
        return redirect(url_for('login'))

    try:
        my_cursor.execute("SELECT city FROM User WHERE user_id = %s", (session['user_id'],))
        city_row = my_cursor.fetchone()
        if not city_row or not city_row[0]:
            flash('City not found for manager.', 'error')
            return redirect(url_for('login'))
        city = city_row[0]

        my_cursor.execute("""
            SELECT 
                po.purchase_order_id,
                po.order_date,
                po.expected_delivery_date,
                po.status,
                s.name,
                w.name,
                COUNT(pod.product_id),
                SUM(pod.quantity * pod.unit_price),
                GROUP_CONCAT(CONCAT(p.name, ' (', pod.quantity, ')') SEPARATOR ', ')
            FROM Purchase_order po
            JOIN Supplier s ON po.supplier_id = s.supplier_id
            JOIN Warehouse w ON po.warehouse_id = w.warehouse_id
            LEFT JOIN Purchase_Order_Details pod ON po.purchase_order_id = pod.purchase_order_id
            LEFT JOIN Product p ON pod.product_id = p.product_id
            GROUP BY po.purchase_order_id, po.order_date, po.expected_delivery_date, po.status, s.name, w.name
            ORDER BY po.order_date DESC
        """)
        purchase_orders = [{
            'purchase_order_id': row[0],
            'order_date': row[1],
            'delivery_date': row[2],
            'status': row[3],
            'supplier_name': row[4],
            'warehouse_name': row[5],
            'total_items': row[6],
            'total_amount': float(row[7] or 0),
            'product_list': row[8] or 'No products'
        } for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT p.*, pb.quantity_in_stock, pb.minimum_stock
            FROM Product p
            JOIN Product_Branch pb ON p.product_id = pb.product_id
            JOIN Branch b ON pb.branch_id = b.branch_id
            JOIN Address a ON b.address_id = a.address_id
            WHERE a.city = %s
              AND pb.quantity_in_stock <= pb.minimum_stock
            ORDER BY pb.quantity_in_stock ASC
        """, (city,))
        low_stock = my_cursor.fetchall()

        my_cursor.execute("""
            SELECT o.*, u.name
            FROM `Order` o
            JOIN Customer c ON o.customer_id = c.customer_id
            JOIN User u ON c.user_id = u.user_id
            JOIN Branch b ON o.branch_id = b.branch_id
            JOIN Address a ON b.address_id = a.address_id
            WHERE a.city = %s
            ORDER BY o.sale_date DESC
            LIMIT 10
        """, (city,))
        recent_orders = my_cursor.fetchall()

        my_cursor.execute("""
            SELECT 
                w.name,
                b.name,
                a.street_address,
                a.city,
                a.state,
                wbs.is_primary_supplier
            FROM Warehouse_Branch_Supply wbs
            JOIN Warehouse w ON wbs.warehouse_id = w.warehouse_id
            JOIN Branch b ON wbs.branch_id = b.branch_id
            JOIN Address a ON b.address_id = a.address_id
            WHERE a.city = %s
            ORDER BY w.name, b.name
        """, (city,))
        branches_supplied = [{
            'warehouse_name': row[0],
            'branch_name': row[1],
            'address': f"{row[2]}, {row[3]}, {row[4]}",
            'is_primary_supplier': row[5]
        } for row in my_cursor.fetchall()]

        dashboard_data = {
            'dashboard_type': 'manager',
            'purchase_orders': purchase_orders,
            'low_stock': low_stock,
            'recent_orders': recent_orders,
            'branch': None,
            'primary_supplier': None,
            'sales': None,
            'employees': [],
            'inventory': [],
            'branches_supplied': branches_supplied
        }

        return render_template('dashboard.html', data=dashboard_data)

    except Exception as e:
        flash('Error loading dashboard data', 'error')
        return redirect(url_for('login'))

@app.route('/assign-warehouse', methods=['GET', 'POST'])
def assign_warehouse():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    if session.get('role') != 'manager':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        mydb, my_cursor = get_db_connection()
        
        if request.method == 'POST':
            warehouse_id = request.form.get('warehouse_id')
            my_cursor.execute("""
                UPDATE Manager 
                SET warehouse_id = %s 
                WHERE user_id = %s
            """, (warehouse_id, session['user_id']))
            mydb.commit()
            flash('Warehouse assigned successfully!', 'success')
            return redirect(url_for('manager_dashboard'))
        
        my_cursor.execute("""
            SELECT 
                w.warehouse_id,
                w.name,
                a.city,
                a.state,
                CONCAT(a.street_address, ', ', a.city, ', ', a.state),
                w.capacity,
                CASE 
                    WHEN m.manager_id IS NOT NULL THEN 'Assigned'
                    ELSE 'Available'
                END
            FROM Warehouse w
            JOIN Address a ON w.address_id = a.address_id
            LEFT JOIN Manager m ON w.warehouse_id = m.warehouse_id
            WHERE w.warehouse_id NOT IN (
                SELECT warehouse_id 
                FROM Manager 
                WHERE warehouse_id IS NOT NULL
            )
            ORDER BY a.state, a.city
        """)
        
        warehouses = [{
            'id': w[0],
            'name': w[1],
            'city': w[2],
            'state': w[3],
            'address': w[4],
            'capacity': w[5],
            'status': w[6]
        } for w in my_cursor.fetchall()]
        
        grouped_warehouses = {
            'Gaza Strip': [],
            'West Bank': []
        }
        
        for warehouse in warehouses:
            if warehouse['state'] == 'Gaza Strip':
                grouped_warehouses['Gaza Strip'].append(warehouse)
            else:
                grouped_warehouses['West Bank'].append(warehouse)
        
        return render_template('assign_warehouse.html', 
                             warehouses=grouped_warehouses,
                             manager_name=session.get('name', 'Manager'))
                             
    except Exception as e:
        flash('Error loading warehouse data', 'error')
        return redirect(url_for('manager_dashboard'))
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            role = request.form.get('role', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            city = request.form.get('city', '').strip()

            if not all([name, email, password, confirm_password, role, phone]):
                flash('All fields are required', 'error')
                return redirect(url_for('signup'))
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('signup'))
            
            my_cursor.execute("SELECT DISTINCT role FROM User")
            valid_roles = [r[0].lower() for r in my_cursor.fetchall()]

            if role not in ['customer', 'owner', 'employee', 'manager']:
                flash('Invalid role selected', 'error')
                return redirect(url_for('signup'))
            
            my_cursor.execute("SELECT COUNT(*) FROM User WHERE email = %s", (email,))
            if my_cursor.fetchone()[0] > 0:
                flash('Email already registered', 'error')
                return redirect(url_for('signup'))

            if role == 'owner':
                my_cursor.execute("SELECT COUNT(*) FROM User WHERE role = 'owner'")
                if my_cursor.fetchone()[0] > 0:
                    flash('An owner account already exists', 'error')
                    return redirect(url_for('signup'))

            mydb.rollback()

            role_upper = role.upper()
            insert_user_query = """
                INSERT INTO User (email, password, name, role, city)
                VALUES (%s, %s, %s, %s, %s)
            """
            my_cursor.execute(insert_user_query, (email, password, name, role_upper, city if role == 'manager' else None))
            user_id = my_cursor.lastrowid

            if role == 'employee':
                # First get a default warehouse
                my_cursor.execute("SELECT warehouse_id FROM Warehouse LIMIT 1")
                warehouse_result = my_cursor.fetchone()
                if not warehouse_result:
                    # Create a default warehouse if none exists
                    my_cursor.execute("""
                        INSERT INTO Address (street_address, city, state, postal_code)
                        VALUES ('Default Street', 'Default City', 'Default State', '00000')
                    """)
                    address_id = my_cursor.lastrowid
                    
                    my_cursor.execute("""
                        INSERT INTO Warehouse (name, address_id, capacity)
                        VALUES ('Default Warehouse', %s, 1000)
                    """, (address_id,))
                    warehouse_id = my_cursor.lastrowid
                else:
                    warehouse_id = warehouse_result[0]
                
                insert_employee_query = """
                    INSERT INTO Employee (user_id, warehouse_id, phone_number, position, hire_date)
                    VALUES (%s, %s, %s, %s, CURRENT_DATE)
                """
                my_cursor.execute(insert_employee_query, (user_id, warehouse_id, phone, 'Employee'))
                employee_id = my_cursor.lastrowid

            elif role == 'customer':
                insert_customer_query = """
                    INSERT INTO Customer (user_id, phone)
                    VALUES (%s, %s)
                """
                my_cursor.execute(insert_customer_query, (user_id, phone))
                customer_id = my_cursor.lastrowid

            elif role == 'manager':
                my_cursor.execute("""
                    SELECT b.branch_id, a.address_id
                    FROM Branch b
                    JOIN Address a ON b.address_id = a.address_id
                    WHERE a.city = %s
                """, (city,))
                branch_row = my_cursor.fetchone()
                if branch_row:
                    branch_id = branch_row[0]
                    address_id = branch_row[1]
                else:
                    default_street = f"Main Street ({city})"
                    default_state = 'West Bank' if city not in ['Gaza City', 'Khan Yunis', 'Rafah'] else 'Gaza Strip'
                    default_postal = '00970'
                    my_cursor.execute("""
                        INSERT INTO Address (street_address, city, state, postal_code)
                        VALUES (%s, %s, %s, %s)
                    """, (default_street, city, default_state, default_postal))
                    address_id = my_cursor.lastrowid
                    branch_name = f"{city} Branch"
                    my_cursor.execute("""
                        INSERT INTO Branch (address_id, name)
                        VALUES (%s, %s)
                    """, (address_id, branch_name))
                    branch_id = my_cursor.lastrowid

                my_cursor.execute("""
                    INSERT INTO Manager (user_id, phone)
                    VALUES (%s, %s)
                """, (user_id, phone))
                manager_id = my_cursor.lastrowid

            mydb.commit()
            session.clear()
            session['user_id'] = user_id
            session['email'] = email
            session['name'] = name
            session['role'] = role

            flash('Account created successfully!', 'success')
        
            if role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif role == 'employee':
                return redirect(url_for('employee_dashboard'))
            elif role == 'customer':
                return redirect(url_for('customer_dashboard'))
            elif role == 'owner':
                return redirect(url_for('owner_dashboard'))
            
        except mysql.connector.Error as e:
            try:
                mydb.rollback()
            except Exception as rollback_error:
                pass
            flash('Error creating account. Please try again.', 'error')
            return redirect(url_for('signup'))
            
        except Exception as e:
            try:
                mydb.rollback()
            except Exception as rollback_error:
                pass
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        try:
            my_cursor.execute("""
                UPDATE User 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE user_id = %s
            """, (session['user_id'],))
            mydb.commit()
        except Exception:
            pass
    
    session.clear()
    return redirect(url_for('index'))

@app.route('/customer-dashboard')
def customer_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    if session.get('role') != 'customer':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    try:
        mydb, _ = get_db_connection()          
        my_cursor = mydb.cursor(dictionary=True)

        my_cursor.execute("""
            SELECT c.*,
                u.name  AS user_name,
                u.email AS user_email,
                a.street_address,
                a.city,
                a.state,
                a.postal_code,
                a.country,
                COUNT(DISTINCT o.order_id)       AS total_orders,
                COALESCE(SUM(o.total_amount), 0) AS total_spent,
                MAX(o.sale_date)                 AS last_order_date
            FROM Customer c
            JOIN User u         ON c.user_id   = u.user_id
            LEFT JOIN Address a ON u.address_id = a.address_id
            LEFT JOIN `Order` o ON c.customer_id = o.customer_id
            WHERE c.user_id = %s
            GROUP BY c.customer_id, u.name, u.email,
                    a.street_address, a.city, a.state, a.postal_code, a.country
        """, (session['user_id'],))
        customer_data = my_cursor.fetchone()
        
        if not customer_data:
            flash('Customer profile not found', 'error')
            return render_template('dashboard.html', data={
                'customer': {
                    'name': session.get('name', 'Customer'),
                    'email': session.get('email', ''),
                    'phone': '',
                    'total_orders': 0,
                    'total_spent': 0,
                    'last_order_date': None
                },
                'recent_orders': [],
                'dashboard_type': 'customer'
            })

        my_cursor.execute("""
            SELECT o.order_id, o.sale_date, o.total_amount,
                   b.name AS branch_name, o.status
            FROM `Order` o
            JOIN Branch b ON o.branch_id = b.branch_id
            WHERE o.customer_id = (
                SELECT customer_id FROM Customer WHERE user_id = %s
            )
            ORDER BY o.sale_date DESC
            LIMIT 5
        """, (session['user_id'],))
        order_rows = my_cursor.fetchall()

        recent_orders = []
        for order in order_rows:
            my_cursor.execute("""
                SELECT p.name, od.quantity_sold
                FROM Order_Details od
                JOIN Product p ON od.product_id = p.product_id
                WHERE od.order_id = %s
            """, (order['order_id'],))
            products = [
                {'name': row['name'], 'quantity': row['quantity_sold']}
                for row in my_cursor.fetchall()
            ]
            recent_orders.append({
                'id':     order['order_id'],
                'date':   order['sale_date'],
                'status': order['status'],
                'products': products,
                'total':  float(order['total_amount'] or 0),
                'branch': order['branch_name'],
            })

        my_cursor.execute("""
            SELECT COUNT(DISTINCT o.branch_id) AS branch_count
            FROM `Order` o
            WHERE o.customer_id = (
                SELECT customer_id FROM Customer WHERE user_id = %s
            )
        """, (session['user_id'],))
        total_branches = my_cursor.fetchone()['branch_count']

        my_cursor.execute("""
            SELECT COALESCE(SUM(od.quantity_sold), 0) AS qty_total
            FROM Order_Details od
            JOIN `Order` o ON od.order_id = o.order_id
            WHERE o.customer_id = (
                SELECT customer_id FROM Customer WHERE user_id = %s
            )
        """, (session['user_id'],))
        total_products = my_cursor.fetchone()['qty_total']
        address_parts = [
            customer_data.get('street_address'),
            customer_data.get('city'),
            customer_data.get('state'),
            customer_data.get('postal_code'),
            customer_data.get('country')
        ]
        pretty_address = ', '.join([p for p in address_parts if p]) or None

        dashboard_data = {
            'customer': {
                'name':  customer_data['user_name'],
                'email': customer_data['user_email'],
                'phone': customer_data['phone'],
                'address': pretty_address, 
                'total_orders': customer_data['total_orders'] or 0,
                'total_spent':  float(customer_data['total_spent'] or 0),
                'last_order_date': customer_data['last_order_date']
            },
            'recent_orders': recent_orders,
            'dashboard_type': 'customer',
            'total_branches': total_branches,
            'total_products': total_products
        }

        return render_template('dashboard.html', data=dashboard_data)

    except Exception:
        flash('Error loading dashboard data', 'error')
        return render_template('dashboard.html', data={
            'customer': {
                'name': session.get('name', 'Customer'),
                'email': session.get('email', ''),
                'phone': '',
                'total_orders': 0,
                'total_spent': 0,
                'last_order_date': None
            },
            'recent_orders': [],
            'dashboard_type': 'customer'
        })

# ------------------------------------------------------------------
# OWNER DASHBOARD
# ------------------------------------------------------------------
@app.route('/owner-dashboard')
def owner_dashboard():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('You must be logged in as an owner to access this page.', 'danger')
        return redirect(url_for('login'))

    try:
        # ----------------------------------------------------------
        # 1. Employees
        # ----------------------------------------------------------
        my_cursor.execute("""
            SELECT  e.employee_id,
                    u.name,
                    u.email,
                    e.phone_number,
                    e.position,
                    e.salary,
                    e.hire_date,
                    w.name AS warehouse,
                    b.name AS branch
            FROM Employee e
            JOIN User u              ON e.user_id = u.user_id
            LEFT JOIN Warehouse w    ON e.warehouse_id = w.warehouse_id
            LEFT JOIN Employee_Branch eb ON e.employee_id = eb.employee_id
            LEFT JOIN Branch b       ON eb.branch_id = b.branch_id
            ORDER BY u.name
        """)
        employees = [{
            'id'       : r[0],
            'name'     : r[1],
            'email'    : r[2],
            'phone'    : r[3],
            'position' : r[4],
            'salary'   : float(r[5]) if r[5] else 0.0,
            'hire_date': r[6],
            'warehouse': r[7] or 'Not Assigned',
            'branch'   : r[8] or 'Not Assigned'
        } for r in my_cursor.fetchall()]

        # ----------------------------------------------------------
        # 2. Warehouses
        # ----------------------------------------------------------
        my_cursor.execute("""
            SELECT  w.warehouse_id,
                    w.name,
                    w.capacity,
                    CONCAT(a.street_address, ', ', a.city, ', ', a.state, ' ', a.postal_code) AS address,
                    u.name AS manager
            FROM Warehouse w
            JOIN Address a         ON w.address_id  = a.address_id
            LEFT JOIN Manager m    ON w.warehouse_id = m.warehouse_id
            LEFT JOIN User u       ON m.user_id      = u.user_id
            ORDER BY w.warehouse_id
        """)
        warehouses = []
        for w in my_cursor.fetchall():
            my_cursor.execute("""
                SELECT COUNT(DISTINCT product_id),
                       COALESCE(SUM(quantity_in_stock), 0)
                FROM Product_Warehouse
                WHERE warehouse_id = %s
            """, (w[0],))
            prod_count, used = my_cursor.fetchone()
            pct = round((used / w[2] * 100) if w[2] else 0, 1)
            warehouses.append({
                'id'               : w[0],
                'name'             : w[1],
                'capacity'         : w[2],
                'address'          : w[3],
                'manager'          : w[4] or 'Not Assigned',
                'total_products'   : prod_count,
                'storage_used'     : used,
                'storage_percentage': pct
            })

        # ----------------------------------------------------------
        # 3. Branches  (address + manager now included)
        # ----------------------------------------------------------
        my_cursor.execute("""
            SELECT  b.branch_id,
                    b.name,
                    CONCAT(a.street_address, ', ', a.city, ', ', a.state, ' ', a.postal_code) AS address,
                    u.name AS manager,
                    COUNT(DISTINCT e.employee_id) AS emp_cnt,
                    COUNT(DISTINCT o.order_id)    AS order_cnt,
                    COALESCE(SUM(o.total_amount), 0)        AS revenue,
                    COALESCE(SUM(o.profit_generated), 0)    AS profit
            FROM Branch b
            JOIN Address a           ON b.address_id = a.address_id
            LEFT JOIN Manager m      ON b.manager_id = m.manager_id
            LEFT JOIN User u         ON m.user_id    = u.user_id
            LEFT JOIN Employee_Branch eb ON b.branch_id = eb.branch_id
            LEFT JOIN Employee e     ON eb.employee_id = e.employee_id
            LEFT JOIN `Order` o      ON b.branch_id    = o.branch_id
            GROUP BY b.branch_id, address, manager
        """)
        branches = [{
            'id'       : r[0],
            'name'     : r[1],
            'address'  : r[2] or 'N/A',
            'manager'  : r[3] or 'Not Assigned',
            'employees': r[4] or 0,
            'orders'   : r[5] or 0,
            'revenue'  : float(r[6] or 0),
            'profit'   : float(r[7] or 0)
        } for r in my_cursor.fetchall()]

        # ----------------------------------------------------------
        # 4. Suppliers  (now includes email)
        # ----------------------------------------------------------
        my_cursor.execute("""
            SELECT  s.name,
                    s.email,
                    s.phone_number,
                    CONCAT(a.street_address, ', ', a.city, ', ', a.state, ' ', a.postal_code) AS address
            FROM Supplier s
            LEFT JOIN Address a ON s.address_id = a.address_id
            ORDER BY s.name
        """)
        suppliers = [{
            'name'   : r[0],
            'email'  : r[1] or 'N/A',
            'phone'  : r[2] or 'N/A',
            'address': r[3] or 'N/A'
        } for r in my_cursor.fetchall()]

        # ----------------------------------------------------------
        # 5. Global stats
        # ----------------------------------------------------------
        my_cursor.execute("SELECT COUNT(*) FROM Branch")
        total_branches = my_cursor.fetchone()[0]

        my_cursor.execute("SELECT COUNT(*) FROM Employee")
        total_employees = my_cursor.fetchone()[0]

        my_cursor.execute("SELECT COUNT(*) FROM Product")
        total_products = my_cursor.fetchone()[0]

        my_cursor.execute("SELECT COUNT(*) FROM `Order`")
        total_orders = my_cursor.fetchone()[0]

        my_cursor.execute("""
            SELECT  COALESCE(SUM(total_amount), 0),
                    COALESCE(SUM(profit_generated), 0)
            FROM `Order`
        """)
        total_revenue, total_profit = my_cursor.fetchone()

        # ----------------------------------------------------------
        # 6. Purchase-order summary + list
        # ----------------------------------------------------------
        my_cursor.execute("""
            SELECT  COUNT(*),
                    SUM(status='pending'),
                    SUM(status='approved'),
                    SUM(status='received')
            FROM Purchase_Order
        """)
        po_summary = my_cursor.fetchone()

        my_cursor.execute("""
            SELECT  po.purchase_order_id,
                    po.order_date,
                    po.expected_delivery_date,
                    po.status,
                    s.name,
                    w.name,
                    COUNT(pod.product_id),
                    SUM(pod.quantity * pod.unit_price),
                    GROUP_CONCAT(CONCAT(p.name,' (',pod.quantity,')') SEPARATOR ', ')
            FROM Purchase_Order po
            JOIN Supplier s ON po.supplier_id  = s.supplier_id
            JOIN Warehouse w ON po.warehouse_id = w.warehouse_id
            LEFT JOIN Purchase_Order_Details pod ON po.purchase_order_id = pod.purchase_order_id
            LEFT JOIN Product p ON pod.product_id = p.product_id
            GROUP BY po.purchase_order_id
            ORDER BY po.order_date DESC
        """)
        purchase_orders = [{
            'purchase_order_id': r[0],
            'order_date'       : r[1],
            'expected_delivery_date': r[2],
            'status'           : r[3],
            'supplier_name'    : r[4],
            'warehouse_name'   : r[5],
            'total_items'      : r[6],
            'total_amount'     : float(r[7] or 0),
            'product_list'     : r[8] or 'No products'
        } for r in my_cursor.fetchall()]

        # ----------------------------------------------------------
        # 7. Bundle + render
        # ----------------------------------------------------------
        dashboard_data = {
            'dashboard_type': 'owner',
            'stats': {
                'total_branches' : total_branches,
                'total_employees': total_employees,
                'total_products' : total_products,
                'total_orders'   : total_orders,
                'total_revenue'  : float(total_revenue or 0),
                'total_profit'   : float(total_profit  or 0)
            },
            'branches'       : branches,
            'warehouses'     : warehouses,
            'employees'      : employees,
            'po_summary'     : po_summary,
            'purchase_orders': purchase_orders,
            'suppliers'      : suppliers
        }

        return render_template('dashboard.html', data=dashboard_data)

    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'danger')
        return redirect(url_for('login'))

from flask import jsonify, abort

@app.route('/sales-profit-data')
def sales_profit_data():
    if 'user_id' not in session or session.get('role') != 'owner':
        abort(403)

    my_cursor.execute("""
        SELECT 
            b.name,
            COALESCE(SUM(o.total_amount), 0)  AS revenue,
            COALESCE(SUM(o.profit_generated), 0) AS profit
        FROM Branch b
        LEFT JOIN `Order` o ON b.branch_id = o.branch_id
        GROUP BY b.branch_id, b.name
        ORDER BY b.name
    """)
    rows = my_cursor.fetchall()

    data = [
        {"name": r[0], "revenue": float(r[1]), "profit": float(r[2])}
        for r in rows
    ]
    return jsonify(data)

from flask import request

@app.route('/orders-data')
def orders_data():
    if 'user_id' not in session:
        abort(403)
    role = session.get('role')
    if role not in ('owner', 'manager', 'employee'):
        abort(403)
    search = request.args.get('search', '').strip()
    params = []
    sql = """
        SELECT o.order_id,
               DATE_FORMAT(o.sale_date,'%Y-%m-%d %H:%i') AS sale_date,
               b.name,
               u.name,
               o.total_amount,
               o.profit_generated,
               o.status
        FROM `Order` o
        LEFT JOIN Branch   b ON o.branch_id   = b.branch_id
        LEFT JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN User     u ON c.user_id     = u.user_id
    """
    if search:
        sql += """
            WHERE o.order_id LIKE %s
               OR b.name LIKE %s
               OR u.name LIKE %s
        """
        like = f"%{search}%"
        params = [like, like, like]
    sql += " ORDER BY o.sale_date DESC"
    my_cursor.execute(sql, params)
    rows = my_cursor.fetchall()
    data = [
        {
            "order_id":      r[0],
            "sale_date":     r[1],
            "branch":        r[2] or 'N/A',
            "customer":      r[3] or 'Walk-in',
            "total":         float(r[4] or 0),
            "profit":        float(r[5] or 0),
            "status":        r[6]
        } for r in rows
    ]
    return jsonify(data)


@app.route('/employee-dashboard')
def employee_dashboard():
    # 1️⃣  Basic auth
    if 'user_id' not in session or session.get('role') != 'employee':
        flash('Please log in as an employee first.', 'error')
        return redirect(url_for('login'))

    try:
        mydb, _ = get_db_connection()
        cur = mydb.cursor(dictionary=True)          # every row is a dict

        # 2️⃣  Employee core data + current branch
        cur.execute("""
            SELECT  e.employee_id,
                    e.phone_number,
                    e.position,
                    u.name        AS user_name,
                    u.email       AS user_email,
                    b.branch_id,
                    b.name        AS branch_name
            FROM Employee e
            JOIN User u                  ON e.user_id = u.user_id
            LEFT JOIN Employee_Branch eb ON e.employee_id = eb.employee_id
            LEFT JOIN Branch b           ON eb.branch_id   = b.branch_id
            WHERE e.user_id = %s
              AND (eb.end_date IS NULL OR eb.end_date > CURRENT_DATE)
            LIMIT 1
        """, (session['user_id'],))
        emp = cur.fetchone()

        # Guard: un-assigned employee
        if not emp or not emp['branch_id']:
            flash('You are not assigned to any branch.', 'error')
            return render_template('dashboard.html',
                                   data={'employee': {'name': emp['user_name'] if emp else 'Employee'},
                                         'dashboard_type': 'employee'})

        branch_id = emp['branch_id']

        # 3️⃣  Today's high-level numbers
        cur.execute("""
            SELECT  COUNT(*)                      AS today_orders,
                    COALESCE(SUM(total_amount),0) AS today_revenue
            FROM `Order`
            WHERE branch_id = %s 
              AND DATE(sale_date) = CURDATE()
        """, (branch_id,))
        stats = cur.fetchone()

        # 4️⃣  Low-stock products
        cur.execute("""
            SELECT p.product_id,
                   p.name,
                   pb.quantity_in_stock,
                   pb.minimum_stock
            FROM Product_Branch pb
            JOIN Product p ON pb.product_id = p.product_id
            WHERE pb.branch_id = %s
              AND pb.quantity_in_stock <= pb.minimum_stock
            ORDER BY pb.quantity_in_stock
            LIMIT 5
        """, (branch_id,))
        low_stock = cur.fetchall()

        # 5️⃣  Five most recent orders (note: Customer.phone column is `phone`)
        cur.execute("""
            SELECT o.order_id,
                   o.sale_date,
                   o.total_amount,
                   u.name   AS customer_name,
                   c.phone  AS customer_phone,
                   COUNT(od.order_detail_id) AS items
            FROM `Order` o
            JOIN Customer      c  ON o.customer_id = c.customer_id
            JOIN User          u  ON c.user_id     = u.user_id
            LEFT JOIN Order_Details od ON o.order_id = od.order_id
            WHERE o.branch_id = %s
            GROUP BY o.order_id
            ORDER BY o.sale_date DESC
            LIMIT 5
        """, (branch_id,))
        recent_orders = cur.fetchall()

        # 6️⃣  Today's sales split by category
        cur.execute("""
            SELECT p.category,
                   COUNT(*)                                   AS items_sold,
                   SUM(od.quantity_sold * od.unit_price)      AS revenue,
                   SUM(od.quantity_sold * 
                       (od.unit_price - p.cost_price))        AS profit
            FROM `Order` o
            JOIN Order_Details od ON o.order_id  = od.order_id
            JOIN Product        p  ON od.product_id = p.product_id
            WHERE o.branch_id = %s
              AND DATE(CONVERT_TZ(sale_date, '+00:00', @@session.time_zone)) = CURDATE()

            GROUP BY p.category
        """, (branch_id,))
        today_sales = cur.fetchall()
        # 7️⃣ Customers for dropdown
        cur.execute("""
            SELECT c.customer_id, u.name, c.phone
            FROM Customer c
            JOIN User u ON c.user_id = u.user_id
            ORDER BY u.name
        """)
        customers = cur.fetchall()

        # 8️⃣ Products for dropdown
        cur.execute("""
            SELECT product_id, name, price
            FROM Product
            ORDER BY name
        """)
        products = cur.fetchall()

        # 5️⃣-b  Orders processed by the logged-in employee (last 5)
        cur.execute("""
            SELECT  o.order_id,
                    o.sale_date,
                    o.total_amount,
                    u.name                     AS customer_name,
                    COUNT(od.order_detail_id)  AS items
            FROM `Order`            o
            JOIN Customer           c  ON o.customer_id = c.customer_id
            JOIN User               u  ON c.user_id     = u.user_id
            LEFT JOIN Order_Details od ON o.order_id    = od.order_id
            WHERE o.processed_by = %s        -- current employee's user_id
            AND o.branch_id    = %s        -- optional: keep it branch-local
            GROUP BY o.order_id
            ORDER BY o.sale_date DESC
            LIMIT 5
        """, (session['user_id'], branch_id))
        my_orders = cur.fetchall()

        # 7️⃣  Package everything for Jinja
        dashboard_data = {
            'dashboard_type': 'employee',
            'my_orders'     : my_orders, 
            'customers': customers,
            'products' : products,
            'employee': {
                'name'    : emp['user_name'],
                'email'   : emp['user_email'],
                'phone'   : emp['phone_number'],
                'position': emp['position'],
                'branch'  : emp['branch_name'] or 'Not assigned'
            },
            'today_orders'  : stats['today_orders'],
            'today_revenue' : float(stats['today_revenue']),
            'pending_orders': 0,                
            'low_stock'     : low_stock,
            'recent_orders' : recent_orders,
            'today_sales'   : today_sales
        }

        return render_template('dashboard.html', data=dashboard_data)

    except Exception as e:
        print("⚠️  employee_dashboard error:", e)
        flash('Error loading dashboard data.', 'error')
        return render_template('dashboard.html',
                               data={'employee': {'name': 'Employee'},
                                     'dashboard_type': 'employee'})


@app.route('/warehouse-dashboard')
def warehouse_dashboard():
    try:
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))

        if session.get('role') not in ['manager', 'warehouse', 'owner']:
            flash('Access denied', 'error')
            return redirect(url_for('login'))

        mydb, my_cursor = get_db_connection()

        my_cursor.execute("""
            SELECT s.name, s.phone_number, a.street_address, a.city, a.state, a.postal_code
            FROM Supplier s
            JOIN Address a ON s.address_id = a.address_id
            ORDER BY s.name
        """)
        suppliers = [{
            'name': row[0],
            'phone': row[1],
            'address': f"{row[2]}, {row[3]}, {row[4]} {row[5]}"
        } for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT w.warehouse_id, w.name, w.capacity,
                   a.street_address, a.city, a.state, a.postal_code
            FROM Warehouse w
            JOIN Address a ON w.address_id = a.address_id
            JOIN Manager m ON w.warehouse_id = m.warehouse_id
            WHERE m.user_id = %s
        """, (session['user_id'],))
        warehouse_data = my_cursor.fetchone()

        if not warehouse_data:
            flash('No warehouse assigned to you yet.', 'info')
            return render_template('dashboard.html', data={
                'dashboard_type': 'warehouse',
                'warehouse': None,
                'storage_used': 0,
                'storage_used_percentage': 0,
                'total_products': 0,
                'inventory': [],
                'purchase_orders': [],
                'suppliers': suppliers,
                'branches_supplied': [],
                'branch_transfers': []
            })

        warehouse_id = warehouse_data[0]
        warehouse = {
            'name': warehouse_data[1],
            'capacity': warehouse_data[2],
            'address': f"{warehouse_data[3]}, {warehouse_data[4]}, {warehouse_data[5]} {warehouse_data[6]}",
            'city': warehouse_data[4]
        }

        my_cursor.execute("""
            SELECT pw.product_id, p.name, pw.quantity_in_stock, pw.minimum_stock, pw.maximum_stock
            FROM Product_Warehouse pw
            JOIN Product p ON pw.product_id = p.product_id
            WHERE pw.warehouse_id = %s
        """, (warehouse_id,))
        inventory = [{
            'product_id': row[0],
            'name': row[1],
            'current_stock': row[2],
            'minimum_stock': row[3],
            'maximum_stock': row[4],
            'status': 'low' if row[2] <= row[3] else ('well stocked' if row[2] >= row[4] else 'normal')
        } for row in my_cursor.fetchall()]

        storage_used = sum(item['current_stock'] for item in inventory)
        storage_used_percentage = (storage_used / warehouse['capacity'] * 100) if warehouse['capacity'] > 0 else 0
        total_products = len(inventory)

        my_cursor.execute("""
            SELECT 
                po.purchase_order_id,
                po.order_date,
                po.expected_delivery_date,
                po.status,
                s.name as supplier_name,
                w.name as warehouse_name,
                COUNT(pod.product_id) as total_items,
                SUM(pod.quantity * pod.unit_price) as total_amount,
                GROUP_CONCAT(CONCAT(p.name, ' (', pod.quantity, ')') SEPARATOR ', ') as product_list
            FROM Purchase_Order po
            JOIN Supplier s ON po.supplier_id = s.supplier_id
            JOIN Warehouse w ON po.warehouse_id = w.warehouse_id
            LEFT JOIN Purchase_Order_Details pod ON po.purchase_order_id = pod.purchase_order_id
            LEFT JOIN Product p ON pod.product_id = p.product_id
            GROUP BY po.purchase_order_id, po.order_date, po.expected_delivery_date, 
                     po.status, s.name, w.name
            ORDER BY po.order_date DESC
        """)
        purchase_orders = [{
            'purchase_order_id': row[0],
            'order_date': row[1],
            'expected_delivery_date': row[2],
            'status': row[3],
            'supplier_name': row[4],
            'warehouse_name': row[5],
            'total_items': row[6],
            'total_amount': float(row[7] or 0),
            'product_list': row[8] or 'No products'
        } for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT 
                b.branch_id,
                b.name as branch_name,
                a.street_address,
                a.city,
                a.state,
                a.postal_code,
                wbs.is_primary_supplier
            FROM Warehouse_Branch_Supply wbs
            JOIN Branch b ON wbs.branch_id = b.branch_id
            JOIN Address a ON b.address_id = a.address_id
            WHERE wbs.warehouse_id = %s
            ORDER BY b.name
        """, (warehouse_id,))
        branches_supplied = [{
            'branch_id': row[0],
            'branch_name': row[1],
            'address': f"{row[2]}, {row[3]}, {row[4]} {row[5]}",
            'is_primary_supplier': row[6]
        } for row in my_cursor.fetchall()]

        dashboard_data = {
            'dashboard_type': 'warehouse',
            'warehouse': warehouse,
            'storage_used': storage_used,
            'storage_used_percentage': storage_used_percentage,
            'total_products': total_products,
            'inventory': inventory,
            'purchase_orders': purchase_orders,
            'suppliers': suppliers,
            'branches_supplied': branches_supplied,
            'branch_transfers': []
        }

        return render_template('dashboard.html', data=dashboard_data)

    except Exception as e:
        flash('Error loading warehouse dashboard', 'error')
        return render_template('dashboard.html', data={
            'dashboard_type': 'warehouse',
            'warehouse': None,
            'storage_used': 0,
            'storage_used_percentage': 0,
            'total_products': 0,
            'inventory': [],
            'purchase_orders': [],
            'suppliers': [],
            'branches_supplied': [],
            'branch_transfers': []
        })

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash('Please log in as a customer to add to cart.', 'error')
        return redirect(url_for('login'))

    product_id = str(request.form['product_id'])
    quantity = int(request.form['quantity'])

    cart = session.get('cart', {})
    if product_id in cart:
        cart[product_id] += quantity
    else:
        cart[product_id] = quantity

    session['cart'] = cart

    flash('Product added to cart.', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/new_order')
def new_order():
    cur = mydb.cursor(dictionary=True)
    cur.execute("SELECT * FROM Product")
    products = cur.fetchall()
    return render_template('new_order.html', products=products)

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    if not cart:
        return render_template('cart.html', products=[], cart={}, grand_total=0)

    ids = list(cart.keys())
    placeholders = ','.join(['%s'] * len(ids))
    sql = f"SELECT * FROM Product WHERE product_id IN ({placeholders})"
    my_cursor.execute(sql, ids)
    products = my_cursor.fetchall()

    product_dicts = []
    grand_total = 0
    for prod in products:
        d = {
            'product_id': str(prod[0]),
            'name': prod[1],
            'price': prod[2],
            'category': prod[3],
            'description': prod[4],
        }
        qty = cart.get(str(prod[0]), 0)
        grand_total += d['price'] * qty
        product_dicts.append(d)

    return render_template('cart.html', products=product_dicts, cart=cart, grand_total=grand_total)
# Update quantity (+/-)
@app.route('/cart/update/<product_id>', methods=['POST'])
def update_cart(product_id):
    cart = session.get('cart', {})
    action = request.form.get('action')
    if product_id in cart:
        if action == 'increase':
            cart[product_id] += 1
        elif action == 'decrease':
            cart[product_id] -= 1
            if cart[product_id] < 1:
                cart.pop(product_id)
    session['cart'] = cart
    return redirect(url_for('cart'))

# Remove item
@app.route('/cart/remove/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(product_id, None)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id:
        flash("You're not logged in")
        return redirect(url_for('cart'))

    my_cursor.execute("SELECT customer_id FROM Customer WHERE user_id = %s", (user_id,))
    row = my_cursor.fetchone()
    if not row:
        flash("Your account is not registered as a customer.")
        return redirect(url_for('cart'))
    customer_id = row[0]

    cart = session.get('cart', {})
    if not cart:
        flash("Cart is empty", "warning")
        return redirect(url_for('cart'))

    total = 0
    profit_generated = 0
    branch_id = None

    try:
        mydb.rollback()
        mydb.start_transaction()

        my_cursor.execute("""
            SELECT b.branch_id 
            FROM Branch b
            JOIN Address a ON b.address_id = a.address_id
            JOIN User u ON a.city = u.city
            WHERE u.user_id = %s
            LIMIT 1
        """, (user_id,))
        branch_row = my_cursor.fetchone()
        if branch_row:
            branch_id = branch_row[0]

        my_cursor.execute("""
            INSERT INTO `Order` 
            (customer_id, branch_id, sale_date, total_amount, profit_generated, status)
            VALUES (%s, %s, NOW(), 0, 0, 'completed')
        """, (customer_id, branch_id))
        order_id = my_cursor.lastrowid

        for pid, qty in cart.items():
            my_cursor.execute("""
                SELECT price, COALESCE(cost_price, 0) as cost_price 
                FROM Product 
                WHERE product_id = %s
            """, (pid,))
            price_row = my_cursor.fetchone()
            if not price_row:
                raise Exception(f"Product {pid} not found")

            price, cost_price = price_row
            item_total = price * qty
            item_profit = (price - cost_price) * qty

            total += item_total
            profit_generated += item_profit

            my_cursor.execute("""
                INSERT INTO Order_Details 
                (order_id, product_id, quantity_sold, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, pid, qty, price))

            if branch_id:
                my_cursor.execute("""
                    UPDATE Product_Branch 
                    SET quantity_in_stock = quantity_in_stock - %s
                    WHERE product_id = %s AND branch_id = %s
                """, (qty, pid, branch_id))

        my_cursor.execute("""
            UPDATE `Order` 
            SET total_amount = %s, profit_generated = %s
            WHERE order_id = %s
        """, (total, profit_generated, order_id))

        mydb.commit()
        session.pop('cart', None)
        flash("Order placed successfully!", "success")
        return redirect(url_for('cart', success=1))

    except Exception as e:
        mydb.rollback()
        flash(f"Error processing order: {e}", "danger")
        return redirect(url_for('cart'))
@app.route('/category/<category>')
def category_products(category):
    cur = mydb.cursor(dictionary=True)
    cur.execute("SELECT * FROM Product WHERE category = %s", (category,))
    products = cur.fetchall()
    for product in products:
        if 'img_path' not in product or not product['img_path']:
            product['img_path'] = 'default.png'
    return render_template('category_products.html', products=products, category=category)

@app.context_processor
def utility_processor():
    def get_dashboard_url():
        role = session.get('role')
        if role == 'owner':
            return url_for('owner_dashboard')
        elif role == 'manager':
            return url_for('manager_dashboard')
        elif role == 'employee':
            return url_for('employee_dashboard')
        elif role == 'customer':
            return url_for('customer_dashboard')
        return url_for('login')

    return {
        'now': datetime.now,
        'get_dashboard_url': get_dashboard_url
    }

def get_dashboard_url():
    if session.get('role') == 'owner':
        return url_for('owner_dashboard')
    elif session.get('role') == 'manager':
        return url_for('manager_dashboard')
    else:
        return url_for('warehouse_dashboard')

@app.route('/create_purchase_order', methods=['GET', 'POST'])
def create_purchase_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') not in ['owner', 'manager']:
        flash('Access denied. Please login as an owner or manager.', 'error')
        return redirect(get_dashboard_url())
    
    if request.method == 'POST':
        try:
            supplier_id = request.form.get('supplier_id')
            warehouse_id = request.form.get('warehouse_id')
            expected_delivery_date = request.form.get('expected_delivery_date')
            items = request.form.getlist('items[]')
            quantities = request.form.getlist('quantities[]')
            prices = request.form.getlist('prices[]')

            if not all([supplier_id, warehouse_id, expected_delivery_date, items, quantities, prices]):
                missing_fields = []
                if not supplier_id: missing_fields.append('supplier')
                if not warehouse_id: missing_fields.append('warehouse')
                if not expected_delivery_date: missing_fields.append('delivery date')
                if not items: missing_fields.append('items')
                if not quantities: missing_fields.append('quantities')
                if not prices: missing_fields.append('prices')
                flash(f'Missing required fields: {", ".join(missing_fields)}', 'error')
                return redirect(url_for('create_purchase_order'))

            my_cursor.execute("START TRANSACTION")
            try:
                my_cursor.execute("""
                    INSERT INTO Purchase_order 
                    (supplier_id, warehouse_id, expected_delivery_date, status)
                    VALUES (%s, %s, %s, 'pending')
                """, (supplier_id, warehouse_id, expected_delivery_date))
                
                purchase_order_id = my_cursor.lastrowid

                for item_id, quantity, price in zip(items, quantities, prices):
                    my_cursor.execute("""
                        INSERT INTO Purchase_Order_Details 
                        (purchase_order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (purchase_order_id, item_id, quantity, price))

                mydb.commit()
                flash('Purchase order created successfully!', 'success')
                return redirect(get_dashboard_url())

            except Exception as e:
                mydb.rollback()
                flash(f'Database error: {str(e)}', 'error')
                return redirect(url_for('create_purchase_order'))
            
        except Exception as e:
            flash(f'Error creating purchase order: {str(e)}', 'error')
            return redirect(url_for('create_purchase_order'))
    
    try:
        my_cursor.execute("""
            SELECT supplier_id, name 
            FROM Supplier 
            ORDER BY name
        """)
        suppliers = [{'supplier_id': row[0], 'name': row[1]} for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT warehouse_id, name 
            FROM Warehouse 
            ORDER BY name
        """)
        warehouses = [{'warehouse_id': row[0], 'name': row[1]} for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT 
                p.product_id as item_id,
                p.name,
                p.price,
                COALESCE(pw.quantity_in_stock, 0) as current_stock
            FROM Product p
            LEFT JOIN Product_Warehouse pw ON p.product_id = pw.product_id
            ORDER BY p.name
        """)
        items = [{
            'item_id': row[0],
            'name': row[1],
            'price': float(row[2]),
            'current_stock': row[3]
        } for row in my_cursor.fetchall()]

        return render_template('create_purchase_order.html',
                             suppliers=suppliers,
                             warehouses=warehouses,
                             items=items,
                             now=datetime.now())

    except Exception as e:
        flash(f'Error loading purchase order form: {str(e)}', 'error')
        return redirect(get_dashboard_url())

@app.route('/delete_purchase_order/<int:order_id>', methods=['POST'])
def delete_purchase_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') not in ['owner', 'manager']:
        flash('Access denied. Please login as an owner or manager.', 'error')
        return redirect(get_dashboard_url())
    
    try:
        my_cursor.execute("START TRANSACTION")
        try:
            my_cursor.execute("""
                DELETE FROM Purchase_Order_Details 
                WHERE purchase_order_id = %s
            """, (order_id,))
            
            my_cursor.execute("""
                DELETE FROM Purchase_order 
                WHERE purchase_order_id = %s
            """, (order_id,))
            
            mydb.commit()
            flash('Purchase order deleted successfully!', 'success')
            
        except Exception as e:
            mydb.rollback()
            flash(f'Error deleting purchase order: {str(e)}', 'error')
            
    except Exception as e:
        flash(f'Error deleting purchase order: {str(e)}', 'error')
    
    return redirect(get_dashboard_url())

@app.route('/edit_purchase_order/<int:order_id>', methods=['GET', 'POST'])
def edit_purchase_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') not in ['owner', 'manager']:
        flash('Access denied. Please login as an owner or manager.', 'error')
        return redirect(get_dashboard_url())
    
    try:
        if request.method == 'POST':
            supplier_id = request.form.get('supplier_id')
            warehouse_id = request.form.get('warehouse_id')
            expected_delivery_date = request.form.get('expected_delivery_date')
            status = request.form.get('status')
            items = request.form.getlist('items[]')
            quantities = request.form.getlist('quantities[]')
            prices = request.form.getlist('prices[]')

            if not all([supplier_id, warehouse_id, expected_delivery_date, status, items, quantities, prices]):
                missing_fields = []
                if not supplier_id: missing_fields.append('supplier')
                if not warehouse_id: missing_fields.append('warehouse')
                if not expected_delivery_date: missing_fields.append('delivery date')
                if not status: missing_fields.append('status')
                if not items: missing_fields.append('items')
                if not quantities: missing_fields.append('quantities')
                if not prices: missing_fields.append('prices')
                flash(f'Missing required fields: {", ".join(missing_fields)}', 'error')
                return redirect(url_for('edit_purchase_order', order_id=order_id))

            my_cursor.execute("START TRANSACTION")
            try:
                my_cursor.execute("""
                    UPDATE Purchase_order 
                    SET supplier_id = %s,
                        warehouse_id = %s,
                        expected_delivery_date = %s,
                        status = %s
                    WHERE purchase_order_id = %s
                """, (supplier_id, warehouse_id, expected_delivery_date, status, order_id))

                my_cursor.execute("""
                    DELETE FROM Purchase_Order_Details 
                    WHERE purchase_order_id = %s
                """, (order_id,))

                for item_id, quantity, price in zip(items, quantities, prices):
                    my_cursor.execute("""
                        INSERT INTO Purchase_Order_Details 
                        (purchase_order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (order_id, item_id, quantity, price))

                mydb.commit()
                flash('Purchase order updated successfully!', 'success')
                return redirect(get_dashboard_url())

            except Exception as e:
                mydb.rollback()
                flash(f'Error updating purchase order: {str(e)}', 'error')
                return redirect(url_for('edit_purchase_order', order_id=order_id))

        my_cursor.execute("""
            SELECT 
                po.*,
                s.name as supplier_name,
                w.name as warehouse_name
            FROM Purchase_order po
            JOIN Supplier s ON po.supplier_id = s.supplier_id
            JOIN Warehouse w ON po.warehouse_id = w.warehouse_id
            WHERE po.purchase_order_id = %s
        """, (order_id,))
        order = my_cursor.fetchone()

        if not order:
            flash('Purchase order not found', 'error')
            return redirect(get_dashboard_url())

        my_cursor.execute("""
            SELECT 
                pod.product_id,
                pod.quantity,
                pod.unit_price,
                p.name as product_name
            FROM Purchase_Order_Details pod
            JOIN Product p ON pod.product_id = p.product_id
            WHERE pod.purchase_order_id = %s
        """, (order_id,))
        order_details = [{
            'product_id': row[0],
            'quantity': row[1],
            'unit_price': float(row[2]),
            'product_name': row[3]
        } for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT supplier_id, name 
            FROM Supplier 
            ORDER BY name
        """)
        suppliers = [{'supplier_id': row[0], 'name': row[1]} for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT warehouse_id, name 
            FROM Warehouse 
            ORDER BY name
        """)
        warehouses = [{'warehouse_id': row[0], 'name': row[1]} for row in my_cursor.fetchall()]

        my_cursor.execute("""
            SELECT 
                product_id as item_id,
                name,
                price
            FROM Product
            ORDER BY name
        """)
        items = [{
            'item_id': row[0],
            'name': row[1],
            'price': float(row[2])
        } for row in my_cursor.fetchall()]

        order_date = order[3].strftime('%Y-%m-%d') if order[3] else None
        expected_delivery_date = order[4].strftime('%Y-%m-%d') if order[4] else None

        return render_template('edit_purchase_order.html',
                             order={
                                 'purchase_order_id': order[0],
                                 'supplier_id': order[1],
                                 'warehouse_id': order[2],
                                 'order_date': order_date,
                                 'expected_delivery_date': expected_delivery_date,
                                 'status': order[5],
                                 'supplier_name': order[6],
                                 'warehouse_name': order[7]
                             },
                             order_details=order_details,
                             suppliers=suppliers,
                             warehouses=warehouses,
                             items=items,
                             now=datetime.now())

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(get_dashboard_url())
@app.route('/view_purchase_order/<int:order_id>')
def view_purchase_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') not in ['owner', 'manager', 'warehouse']:
        flash('Access denied. Please login with appropriate credentials.', 'error')
        return redirect(get_dashboard_url())
    
    # ... rest of the function ...

@app.route('/process-order/<int:order_id>', methods=['POST'])
def process_order(order_id):
    if 'user_id' not in session or session.get('role') not in ['employee', 'manager']:
        flash('Access denied. Please login as an employee or manager.', 'error')
        return redirect(url_for('login'))

    try:
        my_cursor.execute("START TRANSACTION")

        my_cursor.execute("""
            SELECT o.*, b.branch_id, b.name as branch_name
            FROM `Order` o
            JOIN Branch b ON o.branch_id = b.branch_id
            WHERE o.order_id = %s AND o.status = 'pending'
        """, (order_id,))
        order = my_cursor.fetchone()

        if not order:
            flash('Order not found or already processed', 'error')
            return redirect(url_for('manager_dashboard'))

        my_cursor.execute("""
            SELECT od.*, p.product_id, p.name, p.cost_price
            FROM Order_Details od
            JOIN Product p ON od.product_id = p.product_id
            WHERE od.order_id = %s
        """, (order_id,))
        items = my_cursor.fetchall()

        for item in items:
            my_cursor.execute("""
                UPDATE Product_Branch 
                SET quantity_in_stock = quantity_in_stock - %s
                WHERE product_id = %s AND branch_id = %s
            """, (item['quantity_sold'], item['product_id'], order['branch_id']))

            my_cursor.execute("""
                SELECT quantity_in_stock, minimum_stock
                FROM Product_Branch
                WHERE product_id = %s AND branch_id = %s
            """, (item['product_id'], order['branch_id']))
            stock_info = my_cursor.fetchone()

            if stock_info and stock_info['quantity_in_stock'] <= stock_info['minimum_stock']:
                my_cursor.execute("""
                    INSERT INTO Stock_Alert (product_id, branch_id, alert_type, message)
                    VALUES (%s, %s, 'low_stock', 'Product stock below minimum level')
                """, (item['product_id'], order['branch_id']))

        my_cursor.execute("""
            UPDATE `Order`
            SET status = 'completed', processed_by = %s
            WHERE order_id = %s
        """, (session['user_id'], order_id))

        mydb.commit()
        flash('Order processed successfully!', 'success')
    except Exception as e:
        mydb.rollback()
        flash(f'Error processing order: {str(e)}', 'error')

    return redirect(url_for('manager_dashboard'))

@app.route('/update-inventory/<int:product_id>', methods=['POST'])
def update_inventory(product_id):
    if 'user_id' not in session or session.get('role') not in ['employee', 'manager']:
        flash('Access denied. Please login as an employee or manager.', 'error')
        return redirect(url_for('login'))

    try:
        quantity = int(request.form.get('quantity', 0))
        if quantity <= 0:
            flash('Invalid quantity', 'error')
            return redirect(url_for('manager_dashboard'))

        my_cursor.execute("""
            SELECT b.branch_id
            FROM Branch b
            JOIN Address a ON b.address_id = a.address_id
            JOIN User u ON a.city = u.city
            WHERE u.user_id = %s
        """, (session['user_id'],))
        branch_result = my_cursor.fetchone()

        if not branch_result:
            flash('No branch found for your city', 'error')
            return redirect(url_for('manager_dashboard'))

        branch_id = branch_result[0]

        my_cursor.execute("""
            UPDATE Product_Branch
            SET quantity_in_stock = quantity_in_stock + %s
            WHERE product_id = %s AND branch_id = %s
        """, (quantity, product_id, branch_id))

        my_cursor.execute("""
            INSERT INTO Inventory_Log (product_id, branch_id, quantity_changed, 
                                     changed_by, change_type, notes)
            VALUES (%s, %s, %s, %s, 'manual_adjustment', 'Manual inventory update')
        """, (product_id, branch_id, quantity, session['user_id']))

        mydb.commit()
        flash('Inventory updated successfully!', 'success')
    except Exception as e:
        mydb.rollback()
        flash(f'Error updating inventory: {str(e)}', 'error')

    return redirect(url_for('manager_dashboard'))

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('You must be logged in as an owner to access this page.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            phone = request.form['phone']
            position = request.form['position']
            salary = float(request.form['salary'])
            hire_date = request.form['hire_date']
            warehouse_id = request.form.get('warehouse_id') or None
            branch_id = request.form.get('branch_id') or None

            my_cursor.execute("START TRANSACTION")

            my_cursor.execute("""
                INSERT INTO User (name, email, password, role)
                VALUES (%s, %s, %s, 'employee')
            """, (name, email, password))
            user_id = my_cursor.lastrowid

            my_cursor.execute("""
                INSERT INTO Employee (user_id, phone_number, position, salary, hire_date, warehouse_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, phone, position, salary, hire_date, warehouse_id))
            employee_id = my_cursor.lastrowid

            if branch_id:
                my_cursor.execute("""
                    INSERT INTO Employee_Branch (employee_id, branch_id, start_date)
                    VALUES (%s, %s, %s)
                """, (employee_id, branch_id, hire_date))

            my_cursor.execute("COMMIT")
            flash('Employee added successfully!', 'success')
            return redirect(url_for('owner_dashboard'))

        except Exception as e:
            my_cursor.execute("ROLLBACK")
            flash(f'Error adding employee: {str(e)}', 'danger')
            return redirect(url_for('add_employee'))

    try:
        my_cursor.execute("""
            SELECT warehouse_id as id, name 
            FROM Warehouse 
            ORDER BY name
        """)
        warehouses = my_cursor.fetchall()

        my_cursor.execute("""
            SELECT branch_id as id, name 
            FROM Branch 
            ORDER BY name
        """)
        branches = my_cursor.fetchall()

        return render_template('add_employee.html', 
                             warehouses=warehouses,
                             branches=branches)
    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'danger')
        return redirect(url_for('owner_dashboard'))

@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('You must be logged in as an owner to access this page.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form.get('password')
            phone = request.form['phone']
            position = request.form['position']
            salary = float(request.form['salary'])
            hire_date = request.form['hire_date']
            warehouse_id = request.form.get('warehouse_id') or None
            branch_id = request.form.get('branch_id') or None

            my_cursor.execute("START TRANSACTION")

            my_cursor.execute("""
                SELECT e.employee_id, e.user_id, eb.branch_id
                FROM Employee e
                LEFT JOIN Employee_Branch eb ON e.employee_id = eb.employee_id
                WHERE e.employee_id = %s
            """, (employee_id,))
            current_data = my_cursor.fetchone()
            
            if not current_data:
                raise Exception("Employee not found")

            user_id = current_data[1]
            current_branch_id = current_data[2]

            if password:
                my_cursor.execute("""
                    UPDATE User 
                    SET name = %s, email = %s, password = %s
                    WHERE user_id = %s
                """, (name, email, password, user_id))
            else:
                my_cursor.execute("""
                    UPDATE User 
                    SET name = %s, email = %s
                    WHERE user_id = %s
                """, (name, email, user_id))

            my_cursor.execute("""
                UPDATE Employee 
                SET phone_number = %s, position = %s, salary = %s, 
                    hire_date = %s, warehouse_id = %s
                WHERE employee_id = %s
            """, (phone, position, salary, hire_date, warehouse_id, employee_id))

            if current_branch_id != branch_id:
                if current_branch_id:
                    my_cursor.execute("""
                        DELETE FROM Employee_Branch 
                        WHERE employee_id = %s AND branch_id = %s
                    """, (employee_id, current_branch_id))
                
                if branch_id:
                    my_cursor.execute("""
                        INSERT INTO Employee_Branch (employee_id, branch_id, start_date)
                        VALUES (%s, %s, %s)
                    """, (employee_id, branch_id, hire_date))

            my_cursor.execute("COMMIT")
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('owner_dashboard'))

        except Exception as e:
            my_cursor.execute("ROLLBACK")
            flash(f'Error updating employee: {str(e)}', 'danger')
            return redirect(url_for('edit_employee', employee_id=employee_id))

    try:
        my_cursor.execute("""
            SELECT 
                e.employee_id,
                u.name,
                u.email,
                e.phone_number,
                e.position,
                e.salary,
                e.hire_date,
                e.warehouse_id,
                eb.branch_id
            FROM Employee e
            JOIN User u ON e.user_id = u.user_id
            LEFT JOIN Employee_Branch eb ON e.employee_id = eb.employee_id
            WHERE e.employee_id = %s
        """, (employee_id,))
        employee_data = my_cursor.fetchone()
        
        if not employee_data:
            flash('Employee not found', 'danger')
            return redirect(url_for('owner_dashboard'))

        employee = {
            'id': employee_data[0],
            'name': employee_data[1],
            'email': employee_data[2],
            'phone': employee_data[3],
            'position': employee_data[4],
            'salary': employee_data[5],
            'hire_date': employee_data[6],
            'warehouse_id': employee_data[7],
            'branch_id': employee_data[8],
        }

        my_cursor.execute("SELECT warehouse_id as id, name FROM Warehouse ORDER BY name")
        warehouses = my_cursor.fetchall()

        my_cursor.execute("SELECT branch_id as id, name FROM Branch ORDER BY name")
        branches = my_cursor.fetchall()

        return render_template('edit_employee.html', 
                               employee=employee, 
                               warehouses=warehouses,
                               branches=branches)
    except Exception as e:
        flash(f'Error loading employee data: {str(e)}', 'danger')
    return redirect(url_for('owner_dashboard'))

@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        # First get the user_id associated with this employee
        my_cursor.execute("SELECT user_id FROM Employee WHERE employee_id = %s", (employee_id,))
        result = my_cursor.fetchone()
        
        if not result:
            flash('Employee not found', 'error')
            return redirect(url_for('owner_dashboard'))
        
        user_id = result[0]
        
        # Delete the employee record first (due to foreign key constraints)
        my_cursor.execute("DELETE FROM Employee WHERE employee_id = %s", (employee_id,))
        
        # Then delete the associated user record
        my_cursor.execute("DELETE FROM User WHERE user_id = %s", (user_id,))
        
        mydb.commit()
        flash('Employee deleted successfully', 'success')
    except Exception as e:
        mydb.rollback()
        flash('Error deleting employee', 'error')
    
    return redirect(url_for('owner_dashboard'))

init_db()

@app.route('/create_warehouse', methods=['GET', 'POST'])
def create_warehouse():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    mydb, my_cursor = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        capacity = request.form.get('capacity')
        address_id = request.form.get('address_id')
        my_cursor.execute("""
            INSERT INTO Warehouse (name, capacity, address_id) VALUES (%s, %s, %s)
        """, (name, capacity, address_id))
        mydb.commit()
        flash('Warehouse created successfully!', 'success')
        return redirect(url_for('owner_dashboard'))
    my_cursor.execute("SELECT address_id, street_address, city, state, postal_code FROM Address")
    addresses = my_cursor.fetchall()
    return render_template('create_warehouse.html', addresses=addresses)

@app.route('/edit_warehouse/<int:warehouse_id>', methods=['GET', 'POST'])
def edit_warehouse(warehouse_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    mydb, my_cursor = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        capacity = request.form.get('capacity')
        address_id = request.form.get('address_id')
        my_cursor.execute("""
            UPDATE Warehouse SET name=%s, capacity=%s, address_id=%s WHERE warehouse_id=%s
        """, (name, capacity, address_id, warehouse_id))
        mydb.commit()
        flash('Warehouse updated successfully!', 'success')
        return redirect(url_for('owner_dashboard'))
    my_cursor.execute("SELECT name, capacity, address_id FROM Warehouse WHERE warehouse_id=%s", (warehouse_id,))
    warehouse = my_cursor.fetchone()
    my_cursor.execute("SELECT address_id, street_address, city, state, postal_code FROM Address")
    addresses = my_cursor.fetchall()
    return render_template('edit_warehouse.html', warehouse=warehouse, addresses=addresses, warehouse_id=warehouse_id)

@app.route('/delete_warehouse/<int:warehouse_id>', methods=['POST'])
def delete_warehouse(warehouse_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    mydb, my_cursor = get_db_connection()
    try:
        my_cursor.execute("DELETE FROM Warehouse WHERE warehouse_id=%s", (warehouse_id,))
        mydb.commit()
        flash('Warehouse deleted successfully!', 'success')
    except Exception as e:
        if hasattr(e, 'errno') and e.errno == 1451:
            flash('Cannot delete warehouse: it is assigned to one or more managers or related records exist.', 'error')
        else:
            flash(f'Error deleting warehouse: {str(e)}', 'error')
    return redirect(url_for('owner_dashboard'))

@app.route('/create_branch', methods=['GET', 'POST'])
def create_branch():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    mydb, my_cursor = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        address_id = request.form.get('address_id')
        my_cursor.execute("""
            INSERT INTO Branch (name, address_id) VALUES (%s, %s)
        """, (name, address_id))
        mydb.commit()
        flash('Branch created successfully!', 'success')
        return redirect(url_for('owner_dashboard'))
    my_cursor.execute("SELECT address_id, street_address, city, state, postal_code FROM Address")
    addresses = my_cursor.fetchall()
    return render_template('create_branch.html', addresses=addresses)

@app.route('/edit_branch/<int:branch_id>', methods=['GET', 'POST'])
def edit_branch(branch_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    mydb, my_cursor = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        address_id = request.form.get('address_id')
        my_cursor.execute("""
            UPDATE Branch SET name=%s, address_id=%s WHERE branch_id=%s
        """, (name, address_id, branch_id))
        mydb.commit()
        flash('Branch updated successfully!', 'success')
        return redirect(url_for('owner_dashboard'))
    my_cursor.execute("SELECT name, address_id FROM Branch WHERE branch_id=%s", (branch_id,))
    branch = my_cursor.fetchone()
    my_cursor.execute("SELECT address_id, street_address, city, state, postal_code FROM Address")
    addresses = my_cursor.fetchall()
    return render_template('edit_branch.html', branch=branch, addresses=addresses, branch_id=branch_id)

@app.route('/delete_branch/<int:branch_id>', methods=['POST'])
def delete_branch(branch_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    mydb, my_cursor = get_db_connection()
    my_cursor.execute("DELETE FROM Branch WHERE branch_id=%s", (branch_id,))
    mydb.commit()
    flash('Branch deleted successfully!', 'success')
    return redirect(url_for('owner_dashboard'))

def allowed_to_edit():
    return ('user_id' in session and
            session.get('role') in ('manager', 'employee', 'owner'))

@app.route('/add-customer', methods=['GET', 'POST'])
def add_customer():
    if not allowed_to_edit():
        abort(403)

    mydb, my_cursor = get_db_connection()

    if request.method == 'POST':
        addr_sql = """INSERT INTO Address
                      (street_address, city, state, postal_code, country)
                      VALUES (%s,%s,%s,%s,%s)"""
        addr_vals = (request.form['street'],
                     request.form['city'],
                     request.form['state'],
                     request.form['postal'],
                     request.form['country'])
        my_cursor.execute(addr_sql, addr_vals)
        address_id = my_cursor.lastrowid

        user_sql = """INSERT INTO User
                      (email, password, name, role, city)
                      VALUES (%s,%s,%s,'customer',%s)"""
        user_vals = (
            request.form['email'],
            request.form['password'],  
            request.form['full_name'],
            request.form['city']
        )
        my_cursor.execute(user_sql, user_vals)
        user_id = my_cursor.lastrowid

        cust_sql = """INSERT INTO Customer (user_id, phone)
                      VALUES (%s,%s)"""
        my_cursor.execute(cust_sql, (user_id, request.form['phone']))

        mydb.commit()
        flash('Customer added!', 'success')
        return redirect(url_for('employee_dashboard'
                if session['role']=='employee' else 'manager_dashboard'))

    return render_template('add_customer.html')

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if not allowed_to_edit():
        abort(403)

    mydb, my_cursor = get_db_connection()

    if request.method == 'POST':
        prod_sql = """INSERT INTO Product
                      (name, price, cost_price, category, description, img_path)
                      VALUES (%s,%s,%s,%s,%s,%s)"""
        prod_vals = (request.form['name'],
                     request.form['price'],
                     request.form['cost_price'],
                     request.form['category'],
                     request.form['description'],
                     request.form['img_path'] or None)
        my_cursor.execute(prod_sql, prod_vals)
        product_id = my_cursor.lastrowid

        my_cursor.execute("SELECT warehouse_id FROM Warehouse")
        wh_ids = [r[0] for r in my_cursor.fetchall()]
        stock_sql = """INSERT INTO Product_Warehouse
                       (product_id, warehouse_id, quantity_in_stock,
                        minimum_stock, maximum_stock)
                       VALUES (%s,%s,0,0,0)"""
        for wid in wh_ids:
            my_cursor.execute(stock_sql, (product_id, wid))

        mydb.commit()
        flash('Product added!', 'success')
        return redirect(url_for('employee_dashboard'
                if session['role']=='employee' else 'manager_dashboard'))

    return render_template('add_product.html')

if __name__ == '__main__':
    app.run()
