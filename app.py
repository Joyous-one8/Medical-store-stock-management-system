from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change to a real secret key

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'yourpass',
    'database': 'medical_store'
}

# Initialize the database
def initialize_db():
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            cursor = conn.cursor()

            # Create Medications table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Medications (
                med_id INT AUTO_INCREMENT PRIMARY KEY,
                med_name VARCHAR(255) NOT NULL,
                category VARCHAR(255),
                quantity INT NOT NULL,
                expiry_date DATE
            )
            ''')

            # Create Suppliers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Suppliers (
                supplier_id INT AUTO_INCREMENT PRIMARY KEY,
                supplier_name VARCHAR(255) NOT NULL,
                contact_info VARCHAR(255)
            )
            ''')

            # Create Orders table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                order_date DATE NOT NULL,
                supplier_id INT,
                FOREIGN KEY (supplier_id) REFERENCES Suppliers (supplier_id)
            )
            ''')

            # Create OrderDetails table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS OrderDetails (
                order_detail_id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                med_id INT,
                quantity_ordered INT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES Orders (order_id),
                FOREIGN KEY (med_id) REFERENCES Medications (med_id)
            )
            ''')

            # Create Sales table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Sales (
                sale_id INT AUTO_INCREMENT PRIMARY KEY,
                sale_date DATE NOT NULL,
                med_id INT,
                quantity_sold INT NOT NULL,
                FOREIGN KEY (med_id) REFERENCES Medications (med_id)
            )
            ''')

            conn.commit()
            cursor.close()
            conn.close()
            print("Database initialized successfully.")
    except Error as e:
        print(f"Error: '{e}'")

# Function to execute an SQL query with parameters
def execute_query(query, params=()):
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            cursor.close()
            conn.close()
    except Error as e:
        print(f"Error: '{e}'")

# Function to fetch results from an SQL query with parameters
def fetch_query(query, params=()):
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
    except Error as e:
        print(f"Error: '{e}'")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_medication', methods=['GET', 'POST'])
def add_medication():
    if request.method == 'POST':
        med_name = request.form['med_name']
        category = request.form['category']
        quantity = request.form['quantity']
        expiry_date = request.form['expiry_date']
        query = '''
        INSERT INTO Medications (med_name, category, quantity, expiry_date)
        VALUES (%s, %s, %s, %s)
        '''
        params = (med_name, category, quantity, expiry_date)
        execute_query(query, params)
        flash(f'Medication {med_name} added successfully.')
        return redirect(url_for('index'))
    return render_template('add_medication.html')

@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        supplier_name = request.form['supplier_name']
        contact_info = request.form['contact_info']
        query = '''
        INSERT INTO Suppliers (supplier_name, contact_info)
        VALUES (%s, %s)
        '''
        params = (supplier_name, contact_info)
        execute_query(query, params)
        flash(f'Supplier {supplier_name} added successfully.')
        return redirect(url_for('index'))
    return render_template('add_supplier.html')

@app.route('/update_inventory', methods=['GET', 'POST'])
def update_inventory():
    if request.method == 'POST':
        med_id = request.form['med_id']
        new_quantity = request.form['new_quantity']
        query = '''
        UPDATE Medications
        SET quantity = %s
        WHERE med_id = %s
        '''
        params = (new_quantity, med_id)
        execute_query(query, params)
        flash(f'Inventory updated for Medication ID {med_id}.')
        return redirect(url_for('index'))
    return render_template('update_inventory.html')

@app.route('/check_stock')
def check_stock():
    query = '''
    SELECT med_id, med_name, quantity, expiry_date
    FROM Medications
    '''
    medications = fetch_query(query)
    return render_template('check_stock.html', medications=medications)

@app.route('/generate_alerts')
def generate_alerts():
    query = '''
    SELECT med_name, quantity, expiry_date
    FROM Medications
    WHERE quantity < 10 OR expiry_date < CURDATE() + INTERVAL 1 MONTH
    '''
    alerts = fetch_query(query)
    return render_template('generate_alerts.html', alerts=alerts)

@app.route('/record_sale', methods=['GET', 'POST'])
def record_sale():
    if request.method == 'POST':
        med_id = request.form['med_id']
        quantity_sold = request.form['quantity_sold']
        query = '''
        INSERT INTO Sales (sale_date, med_id, quantity_sold)
        VALUES (CURDATE(), %s, %s)
        '''
        params = (med_id, quantity_sold)
        execute_query(query, params)

        update_query = '''
        UPDATE Medications
        SET quantity = quantity - %s
        WHERE med_id = %s
        '''
        update_params = (quantity_sold, med_id)
        execute_query(update_query, update_params)
        flash(f'Sale recorded for Medication ID {med_id}.')
        return redirect(url_for('index'))
    return render_template('record_sale.html')

@app.route('/place_order', methods=['GET', 'POST'])
def place_order():
    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        med_id = request.form['med_id']
        quantity_ordered = request.form['quantity_ordered']

        # Check if supplier exists
        supplier_check_query = 'SELECT COUNT(*) FROM Suppliers WHERE supplier_id = %s'
        supplier_exists = fetch_query(supplier_check_query, (supplier_id,))[0][0]
        if not supplier_exists:
            flash(f"Error: Supplier ID {supplier_id} does not exist.")
            return redirect(url_for('place_order'))

        # Check if medication exists
        med_check_query = 'SELECT COUNT(*) FROM Medications WHERE med_id = %s'
        med_exists = fetch_query(med_check_query, (med_id,))[0][0]
        if not med_exists:
            flash(f"Error: Medication ID {med_id} does not exist.")
            return redirect(url_for('place_order'))

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Start a new transaction
            cursor.execute('START TRANSACTION')

            # Insert order
            query = '''
            INSERT INTO Orders (order_date, supplier_id)
            VALUES (CURDATE(), %s)
            '''
            params = (supplier_id,)
            cursor.execute(query, params)
            conn.commit()

            # Get the last inserted order_id
            order_id = cursor.lastrowid

            # Insert order details
            detail_query = '''
            INSERT INTO OrderDetails (order_id, med_id, quantity_ordered)
            VALUES (%s, %s, %s)
            '''
            detail_params = (order_id, med_id, quantity_ordered)
            cursor.execute(detail_query, detail_params)
            conn.commit()

            # Commit the transaction
            cursor.execute('COMMIT')
            flash(f'Order placed: Supplier ID {supplier_id}, Medication ID {med_id}, Quantity {quantity_ordered}.')
        except Error as e:
            # Rollback the transaction in case of error
            cursor.execute('ROLLBACK')
            flash(f"Error: '{e}'")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('index'))
    return render_template('place_order.html')

if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
