from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from functools import wraps
import os
from config import Config
from database import get_db, hash_password
import phonenumbers

app = Flask(__name__, static_url_path='/static')
app.config.from_object(Config)
app.secret_key = 'welcome home app'

@app.route('/')
def index():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM Role")
            roles = cursor.fetchall()
            if len(roles) == 4:
                flash(f"Database connected successfully!", 'success')
            else :
                flash(f"Database connection failed: Wrong count of roles", 'error')
            conn.close()
            return render_template('index.html')
    except pymysql.Error as e:
        flash(f"Database connection failed: {str(e)}", 'error')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        #Preventing SQL injection using parameterized queries
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                               SELECT p.*, GROUP_CONCAT(r.roleID) as roles
                               FROM Person p
                               LEFT JOIN Act a ON p.username = a.username
                               LEFT JOIN Role as r ON a.roleID = r.roleID
                               WHERE p.username = %s
                               GROUP BY p.username""", (username,))
                user = cursor.fetchone()
                
                if user:
                    stored_password = user['password']
                    salt, hashed = stored_password.split(":")
                    
                    if hash_password(password, salt) == hashed:
                        session['username'] = user['userName']
                        session['roles'] = user['roles'].split(',') if user['roles'] else []
                        session['name'] = f"{user['fname']} {user['lname']}"
                        
                        flash('Login successful', 'success')
                        return redirect(url_for('dashboard'))
                flash('Invalid username or password', 'error')        
                        
        finally:
            conn.close()
        
    return render_template('login.html')

#Function to validate phone numbers 
def validate_phone(number):
    try:
        p = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(p):
            return False
        return True
    except phonenumbers.phonenumberutil.NumberParseException:
        return False

@app.route('/register', methods = ['GET', 'POST'])
def register():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT roleID FROM Role')
            roles = cursor.fetchall()
            
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            fname = request.form.get('fname')
            lname = request.form.get('lname')
            email = request.form.get('email')
            selected_roles = request.form.getlist('roles')
            phones = request.form.getlist('phones')
            
            for phone in phones:
                if not validate_phone(phone):
                    flash(f'Invalid phone number format: {phone}', 'error')
                    return render_template('register.html', roles=roles)
                
            # Check if user is trying to be both staff and volunteer
            if 'staff' in selected_roles and 'volunteer' in selected_roles:
                flash('A person cannot be both staff and volunteer', 'error')
                return render_template('register.html', roles=roles)
                
            salt = os.urandom(16).hex()
            hashed_password = f"{salt}:{hash_password(password, salt)}"
            
            conn = get_db()
            try:
                with conn.cursor() as cursor:
                    #Insert the person details
                    cursor.execute(""" 
                                INSERT INTO Person(username, password, fname, lname, email) VALUES (%s, %s, %s, %s, %s)""", (username, hashed_password, fname, lname, email))
                    
                    #Insert the phone details
                    for phone in phones:
                        cursor.execute("""
                                INSERT INTO PersonPhone(username, phone) VALUES (%s, %s)""", (username, phone))
                    
                    #Insert roles
                    for role in selected_roles:
                        cursor.execute("""
                                    INSERT INTO Act(username, roleID) VALUES (%s, %s)""", (username, role))
                    
                    conn.commit()
                    flash('Registration successful', 'success')
                    return redirect(url_for('login'))
                
            except pymysql.Error as e:
                conn.rollback()
                flash(f'Registration unsuccessful: {str(e)}', 'success')
                
        return render_template('register.html', roles = roles)
    
    finally:
                conn.close()


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            #Fetch items with their locations
            cursor.execute("""
                           SELECT i.*, p.roomNum, p.shelfNum 
                           FROM Item i
                           LEFT JOIN Piece p on i.ItemID = p.ItemID""")
            items = cursor.fetchall()
            
            #Fetch recent orders
            cursor.execute("""
                           SELECT o.*, pc.fname as ClientFName, pc.lname as ClientLName, ps.fname as SupervisorFName, ps.lname as SupervisorLName, d.status
                           FROM Ordered o
                           JOIN Person pc ON o.client = pc.userName
                           JOIN Person ps ON o.supervisor = ps.userName
                           JOIN Delivered d ON o.orderID = d.orderID
                           ORDER BY o.orderDate DESC""")
            orders = cursor.fetchall()
            
            cursor.execute("""
                SELECT i.ItemID, i.iDescription, i.mainCategory, i.subCategory, 
                       i.isNew, d.donateDate, p.fname as DonorFName, 
                       p.lname as DonorLName
                FROM Item i 
                JOIN DonatedBy d ON i.ItemID = d.ItemID
                JOIN Person p ON d.userName = p.userName
                ORDER BY d.donateDate DESC
            """)
            donations = cursor.fetchall()
            
            return render_template('dashboard.html', items = items, orders = orders, donations = donations)
    finally:
        conn.close()

# Function to find the orders (part c)
@app.route('/find-orders')
def find_orders():
    return render_template('find_orders.html')

# Function to find the orders (part c)
@app.route('/findOrderItemsAuth', methods=['GET', 'POST'])
def findOrderItemsAuth():
    orderID = request.form['OrderID']
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            query = '''SELECT 
                    i.ItemID,
                    i.iDescription AS ItemDescription,
                    p.pieceNum,
                    p.pDescription AS PieceDescription,
                    p.roomNum,
                    p.shelfNum,
                    l.shelf AS ShelfName,
                    l.shelfDescription AS ShelfDescription
                FROM 
                    ItemIn ii
                JOIN 
                    Item i ON ii.ItemID = i.ItemID
                LEFT JOIN 
                    Piece p ON i.ItemID = p.ItemID
                LEFT JOIN 
                    Location l ON p.roomNum = l.roomNum AND p.shelfNum = l.shelfNum
                WHERE 
                    ii.orderID = %s'''
            cursor.execute(query, orderID)
            data = cursor.fetchall()
            return render_template('find_orders.html', orders=data)
    finally:
        conn.close()   

@app.route('/find-Items')
def find_items():
    return render_template('Singleitem.html') 

@app.route('/SingleItemAuth', methods=['GET', 'POST'])
def SingleItemAuth():
    #grabs information from the forms
    ItemID = request.form['ItemID']
    # password = request.form['password']
    conn = get_db()
    #cursor used to send queries
    try:
        cursor = conn.cursor()
        #executes query
        query = 'Select ItemID,pDescription, p.roomNum, p.shelfNum,shelf,shelfDescription from Piece p left join Location l on p.roomNum=l.roomNum and p.shelfNum=l.shelfNum where ItemID=%s'
        cursor.execute(query, ItemID)#, password))
        #stores the results in a variable
        data = cursor.fetchall()
        #use fetchall() if you are expecting more than 1 data row
        cursor.close()
        error = None
        # if(data):
        #     #creates a session for the the user
        #     #session is a built in
        #     session['username'] = username
        #     return redirect(url_for('home'))
        # else:
        #     #returns an error message to the html page
        #     error = 'Invalid login or username'
        return render_template('Singleitem.html' ,error=error,posts=data)
    finally:
        conn.close() 

# Ensure the user is logged in and is a staff member
def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or 'staff' not in session.get('roles', []):
            flash('You must be logged in as staff to access this feature.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/start-order', methods=['GET', 'POST'])
@staff_required
def start_order():
    conn = get_db()
    try:
        if request.method == 'POST':
            client_username = request.form.get('client_username')

            # Validate client existence
            with conn.cursor() as cursor:
                cursor.execute("SELECT username FROM Person WHERE username = %s", (client_username,))
                client = cursor.fetchone()

                if not client:
                    flash('Client username does not exist.', 'error')
                    return render_template('start_order.html')

                # Create a new order
                cursor.execute("""
                    INSERT INTO Ordered (client, supervisor, orderDate)
                    VALUES (%s, %s, NOW())
                """, (client_username, session['username']))
                conn.commit()

                # Get the newly created order ID
                cursor.execute("SELECT LAST_INSERT_ID() AS orderID")
                order_id = cursor.fetchone()['orderID']

                # Store order ID in session
                session['orderID'] = order_id
                flash(f"Order created successfully! Order ID: {order_id}", 'success')
                return redirect(url_for('dashboard'))

        return render_template('start_order.html')

    except pymysql.Error as e:
        conn.rollback()
        flash(f"Error creating order: {str(e)}", 'error')
    finally:
        conn.close()




@app.route('/add-to-order', methods=['GET', 'POST'])
@staff_required
def add_to_order():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT mainCategory FROM Item")
            categories = [row['mainCategory'] for row in cursor.fetchall()] or []

            cursor.execute("SELECT DISTINCT subCategory FROM Item")
            subcategories = [row['subCategory'] for row in cursor.fetchall()] or []

        if request.method == 'POST':
            action = request.form.get('action')
            print(action)
            if action == 'find_items':
                # Fetch items based on category and subcategory
                category = request.form['category']
                subcategory = request.form['subcategory']
                print(category)
                print(subcategory)
                #  ItemID = request.form['ItemID']

                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT i.ItemID, i.iDescription 
                        FROM Item i
                        LEFT JOIN ItemIn ii ON i.ItemID = ii.ItemID
                        WHERE ii.orderID IS NULL 
                        AND i.mainCategory = %s 
                        AND i.subCategory = %s
                    """, (category, subcategory))
                    items = cursor.fetchall()

                print("Fetched Items:", items)  # Debugging
                return render_template('add_to_order.html', categories=categories, subcategories=subcategories, items=items, selected_category=category, selected_subcategory=subcategory)

            elif action == 'add_to_order':
                # Add selected item to the current order
                item_id = request.form.get('item_id')
                if not item_id:
                    flash('No item selected. Please select an item to add to the order.', 'error')
                    return redirect(url_for('add_to_order'))

                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO ItemIn (orderID, ItemID)
                        VALUES (%s, %s)
                    """, (session['orderID'], item_id))
                    conn.commit()

                flash(f"Item {item_id} added to order {session['orderID']} successfully!", 'success')
                return redirect(url_for('dashboard'))

        # For GET requests, fetch categories and subcategories
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT mainCategory FROM Item")
            categories = [row['mainCategory'] for row in cursor.fetchall()] or []

            cursor.execute("SELECT DISTINCT subCategory FROM Item")
            subcategories = [row['subCategory'] for row in cursor.fetchall()] or []

        print("Categories:", categories)  # Debugging
        print("Subcategories:", subcategories)  # Debugging

        return render_template('add_to_order.html', categories=categories, subcategories=subcategories, items=None)
    finally:
        conn.close()


# @app.route('/get-items')
# @staff_required
# def get_items():
#     category = request.args.get('category')
#     subcategory = request.args.get('subcategory')

#     conn = get_db()
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute("""
#                 SELECT i.ItemID, i.iDescription
#                 FROM Item i
#                 LEFT JOIN ItemIn ii ON i.ItemID = ii.ItemID
#                 WHERE ii.orderID IS NULL
#                 AND i.mainCategory = %s
#                 AND i.subCategory = %s
#             """, (category, subcategory))
#             items = cursor.fetchall()

#         return jsonify({'items': items})
#     finally:
#         conn.close()

# added feature to prepare orders (part 7)
@app.route('/prepare-order', methods=['GET', 'POST'])
def prepare_order():
    if request.method == 'POST':
        # Get orderID or client username from form
        order_id = request.form.get('orderID')

        try:
            conn = get_db()
            cursor = conn.cursor()

            # If orderID is provided
            if order_id:
                query = """
                    SELECT o.orderID, o.orderDate, o.orderNotes, o.client, o.supervisor
                    FROM Ordered o
                    WHERE o.orderID = %s;
                """
                cursor.execute(query, (order_id,))
            else:
                flash("Please provide an Order ID.")
                return redirect('/prepare-order')

            orders = cursor.fetchall()

            if len(orders) == 0:
                flash("No orders found.")
                return redirect('/prepare-order')

            # Update items in the selected order to 'Holding Area'
            for order in orders:
                update_query = """
                    UPDATE Piece p
                    JOIN ItemIn ii ON p.ItemID = ii.ItemID
                    SET p.roomNum = 999, p.shelfNum = 1, p.pNotes = 'Ready for delivery'
                    WHERE ii.orderID = %s;
                """
                cursor.execute(update_query, (order['orderID'],))

                mark_items_query = """
                    UPDATE Item i
                    JOIN ItemIn ii ON i.ItemID = ii.ItemID
                    SET i.isNew = FALSE
                    WHERE ii.orderID = %s;
                """
                cursor.execute(mark_items_query, (order['orderID'],))

            conn.commit()
            flash("Order prepared successfully.")
        except Exception as e:
            flash(f"Error preparing order: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template('prepare_order.html')


if __name__ == '__main__':
    # app.run( debug = True)
    # app.run('127.0.0.1', 5000, debug = True)
    app.run('127.0.0.1', 5000, debug = True)
     