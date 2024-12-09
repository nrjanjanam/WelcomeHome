from flask import Flask, json, jsonify, render_template, request, redirect, url_for, session, flash
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
                flash(f'Registration unsuccessful: {str(e.args[1])}.', 'error')
                
        return render_template('register.html', roles = roles)
    
    finally:
                conn.close()

@app.route('/logout')
def logout():
    session.clear()
    flash(f'Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/user-details')
@login_required
def user_details():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.*, GROUP_CONCAT(r.roleID) as roles
                FROM Person p
                LEFT JOIN Act a ON p.userName = a.userName
                LEFT JOIN Role r ON a.roleID = r.roleID
                WHERE p.userName = %s
                GROUP BY p.userName
            """, (session['username'],))
            user = cursor.fetchone()
            
            cursor.execute("""
                SELECT phone 
                FROM PersonPhone 
                WHERE userName = %s
            """, (session['username'],))
            phones = cursor.fetchall()
            
        return render_template('user_details.html', user=user, phones=phones)
    finally:
        conn.close()

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # Get total counts for stats
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM Item) as total_items,
                    (SELECT COUNT(*) FROM Ordered) as total_orders,
                    (SELECT COUNT(*) FROM DonatedBy WHERE MONTH(donateDate) = MONTH(CURRENT_DATE())) as monthly_donations,
                    (SELECT COUNT(*) FROM Ordered WHERE MONTH(orderDate) = MONTH(CURRENT_DATE())) as monthly_orders
            """)
            stats = cursor.fetchone()
            
            # Get recent activity
            cursor.execute("""
                SELECT 'Donation' as type, d.donateDate as date, i.iDescription, p.fname, p.lname
                FROM DonatedBy d 
                JOIN Item i ON d.ItemID = i.ItemID
                JOIN Person p ON d.userName = p.userName
                UNION ALL
                SELECT 'Order' as type, o.orderDate as date, NULL as iDescription, p.fname, p.lname
                FROM Ordered o
                JOIN Person p ON o.client = p.userName
                ORDER BY date DESC LIMIT 5
            """)
            recent_activity = cursor.fetchall()
            
        return render_template('dashboard/index.html', 
                             stats=stats,
                             recent_activity=recent_activity)
    finally:
        conn.close()

@app.route('/inventory')
@login_required
def inventory():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT i.*, c.mainCategory, c.subCategory, 
                       p.roomNum, p.shelfNum, l.shelf
                FROM Item i
                LEFT JOIN Category c ON i.mainCategory = c.mainCategory 
                    AND i.subCategory = c.subCategory
                LEFT JOIN Piece p ON i.ItemID = p.ItemID
                LEFT JOIN Location l ON p.roomNum = l.roomNum 
                    AND p.shelfNum = l.shelfNum
                ORDER BY i.itemID
            """)
            items = cursor.fetchall()
        return render_template('dashboard/inventory.html', items=items)
    finally:
        conn.close()

# Added my Orders feature to see personalized view of orders (Part 8)
@app.route('/orders')
@login_required
def orders():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            user_roles = session.get('roles', [])
            username = session['username']
            orders_by_role = {}

            # Client View Query
            if 'client' in user_roles:
                cursor.execute("""
                    SELECT o.orderID, o.orderDate, o.orderNotes,
                           p.fname as SupervisorFName, p.lname as SupervisorLName,
                           GROUP_CONCAT(DISTINCT CONCAT(v.fname, ' ', v.lname)) as volunteers,
                           CASE 
                               WHEN SUM(CASE WHEN d2.status = 'Pending' THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                               WHEN SUM(CASE WHEN d2.status = 'InProgress' THEN 1 ELSE 0 END) > 0 THEN 'InProgress'
                               WHEN COUNT(d2.status) = SUM(CASE WHEN d2.status = 'Delivered' THEN 1 ELSE 0 END) THEN 'Delivered'
                               ELSE 'Pending'
                           END as delivery_status,
                           COUNT(DISTINCT i.ItemID) as item_count
                    FROM Ordered o
                    LEFT JOIN Person p ON o.supervisor = p.userName
                    LEFT JOIN Delivered d ON o.orderID = d.orderID
                    LEFT JOIN Person v ON d.userName = v.userName
                    LEFT JOIN ItemIn i ON o.orderID = i.orderID
                    LEFT JOIN Delivered d2 ON o.orderID = d2.orderID
                    WHERE o.client = %s
                    GROUP BY o.orderID, o.orderDate, o.orderNotes, p.fname, p.lname
                    ORDER BY o.orderDate DESC, orderID DESC
                """, (username,))
                orders_by_role['client'] = cursor.fetchall()

            # Donor View Query
            if 'donor' in user_roles:
                cursor.execute("""
                    SELECT DISTINCT o.orderID, o.orderDate,
                           i.iDescription, db.donateDate,
                           CASE 
                               WHEN SUM(CASE WHEN d2.status = 'Pending' THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                               WHEN SUM(CASE WHEN d2.status = 'InProgress' THEN 1 ELSE 0 END) > 0 THEN 'InProgress'
                               WHEN COUNT(d2.status) = SUM(CASE WHEN d2.status = 'Delivered' THEN 1 ELSE 0 END) THEN 'Delivered'
                               ELSE 'Pending'
                           END as order_status
                    FROM DonatedBy db
                    JOIN Item i ON db.ItemID = i.ItemID
                    JOIN ItemIn ii ON i.ItemID = ii.ItemID
                    JOIN Ordered o ON ii.orderID = o.orderID
                    LEFT JOIN Delivered d ON o.orderID = d.orderID
                    LEFT JOIN Delivered d2 ON o.orderID = d2.orderID
                    WHERE db.userName = %s
                    GROUP BY o.orderID, o.orderDate, i.iDescription, db.donateDate
                    ORDER BY o.orderDate DESC, orderID DESC
                """, (username,))
                orders_by_role['donor'] = cursor.fetchall()

            # Staff View Query - Get all orders they supervise
            if 'staff' in user_roles:
                cursor.execute("""
                SELECT o.orderID, o.orderDate, o.orderNotes, o.supervisor,
                pc.fname as ClientFName, pc.lname as ClientLName,
                GROUP_CONCAT(DISTINCT CONCAT(v.fname, ' ', v.lname)) as volunteers,
                GROUP_CONCAT(DISTINCT v.userName) as volunteer_usernames,
                 CASE 
                               WHEN SUM(CASE WHEN d2.status = 'Pending' THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                               WHEN SUM(CASE WHEN d2.status = 'InProgress' THEN 1 ELSE 0 END) > 0 THEN 'InProgress'
                               WHEN COUNT(d2.status) = SUM(CASE WHEN d2.status = 'Delivered' THEN 1 ELSE 0 END) THEN 'Delivered'
                               ELSE 'Pending'
                           END as delivery_status,
                COUNT(DISTINCT i.ItemID) as item_count,
                GROUP_CONCAT(DISTINCT CONCAT(i.iDescription, ' (', i.color, ')')) as item_details
                    FROM Ordered o
                JOIN Person pc ON o.client = pc.userName
                LEFT JOIN Delivered d ON o.orderID = d.orderID
                LEFT JOIN Person v ON d.userName = v.userName
                LEFT JOIN ItemIn ii ON o.orderID = ii.orderID
                LEFT JOIN Item i ON ii.ItemID = i.ItemID
                LEFT JOIN Delivered d2 ON o.orderID = d2.orderID
                GROUP BY o.orderID, o.orderDate, o.orderNotes, o.supervisor, pc.fname, pc.lname
                ORDER BY o.orderDate DESC, o.orderID DESC
                """)
                orders_by_role['staff'] = cursor.fetchall()

            # Volunteer View Query - Get all orders they deliver
            if 'volunteer' in user_roles:
                cursor.execute("""
                SELECT o.orderID, o.orderDate, o.supervisor,
                p.fname as ClientFName, p.lname as ClientLName,
                ps.fname as SupervisorFName, ps.lname as SupervisorLName,
                CASE 
                               WHEN SUM(CASE WHEN d2.status = 'Pending' THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                               WHEN SUM(CASE WHEN d2.status = 'InProgress' THEN 1 ELSE 0 END) > 0 THEN 'InProgress'
                               WHEN COUNT(d2.status) = SUM(CASE WHEN d2.status = 'Delivered' THEN 1 ELSE 0 END) THEN 'Delivered'
                               ELSE 'Pending'
                           END as delivery_status,
                COUNT(DISTINCT i.ItemID) as item_count,
                GROUP_CONCAT(DISTINCT d.userName) as volunteer_usernames,
                GROUP_CONCAT(DISTINCT CONCAT(i.iDescription, ' (', i.color, ')')) as item_details
                FROM Delivered d
                JOIN Ordered o ON d.orderID = o.orderID
                JOIN Person p ON o.client = p.userName
                JOIN Person ps ON o.supervisor = ps.userName
                LEFT JOIN ItemIn ii ON o.orderID = ii.orderID
                LEFT JOIN Item i ON ii.ItemID = i.ItemID
                LEFT JOIN Delivered d2 ON o.orderID = d2.orderID
                GROUP BY o.orderID, o.orderDate, o.supervisor, p.fname, p.lname, 
                        ps.fname, ps.lname
                ORDER BY o.orderDate DESC, orderID DESC
                """)
                orders_by_role['volunteer'] = cursor.fetchall()

            return render_template('dashboard/orders.html', 
                                orders=orders_by_role, 
                                user_roles=user_roles, 
                                current_user=username)
    finally:
        conn.close()

@app.route('/donations')
@login_required
def donations():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT d.*, i.iDescription, i.mainCategory, i.subCategory, p.fname, p.lname, i.isNew
                FROM DonatedBy d
                JOIN Item i ON d.ItemID = i.ItemID
                JOIN Person p ON d.userName = p.userName
                ORDER BY d.donateDate DESC, i.ItemID DESC
            """)
            donations = cursor.fetchall()
        return render_template('dashboard/donations.html', donations=donations)
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
    return render_template('find_item.html') 

@app.route('/SingleItemAuth', methods=['GET', 'POST'])
def SingleItemAuth():
    # Grab information from the form
    ItemID = request.form.get('ItemID')  # Use get() to handle missing keys gracefully
    if not ItemID:
        return render_template('Singleitem.html', error="ItemID is required.", posts=[])

    conn = get_db()  # Get the database connection

    try:
        cursor = conn.cursor()
        
        # Check if the item has pieces
        piece_check_query = "SELECT COUNT(*) AS piece_count FROM Piece WHERE ItemID = %s"
        cursor.execute(piece_check_query, (ItemID,))
        piece_count = cursor.fetchone()['piece_count']

        if piece_count == 0:
            # If no pieces, fetch basic item details
            item_query = "SELECT ItemID, iDescription FROM Item WHERE ItemID = %s"
            cursor.execute(item_query, (ItemID,))
            item_data = cursor.fetchone()

            # If no item found, return an error
            if not item_data:
                return render_template(
                    'find_item.html',
                    error=f"No data found for ItemID: {ItemID}",
                    posts=[]
                )

            # Return data for items without pieces
            posts = [{
                "ItemID": item_data["ItemID"],
                "iDescription":None,
                "pDescription": item_data["iDescription"],
                "roomNum": None,
                "shelfNum": None,
                "shelf": None,
                "shelfDescription": None
            }]
        else:
            # If pieces exist, fetch item and piece details
            piece_query = """
                SELECT 
                    i.ItemID, 
                    i.iDescription, 
                    p.pDescription, 
                    p.roomNum, 
                    p.shelfNum, 
                    l.shelf, 
                    l.shelfDescription 
                FROM Item i 
                LEFT JOIN Piece p ON i.ItemID = p.ItemID 
                LEFT JOIN Location l ON p.roomNum = l.roomNum AND p.shelfNum = l.shelfNum 
                WHERE i.ItemID = %s
            """
            cursor.execute(piece_query, (ItemID,))
            posts = cursor.fetchall()

        # Render template with data
        return render_template('find_item.html', error=None, posts=posts)

    except Exception as e:
        return render_template('find_item.html', error=f"An error occurred: {str(e)}", posts=[])

    finally:
        conn.close()  # Ensure the connection is always closed

# Ensure the user is logged in and is a staff member
def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or 'staff' not in session.get('roles', []):
            flash('You must be logged in as staff to access this feature.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
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

                # Check if the username is the staff's own username
                if client_username == session['username']:
                    flash('You cannot create an order for yourself.', 'error')
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

                # Insert an initial status entry in the Delivered table
                cursor.execute("""
                    INSERT INTO Delivered (userName, orderID, status, date)
                    VALUES (%s, %s, 'InProgress', NOW())
                """, (session['username'], order_id))
                conn.commit()

                # Store order ID in session
                session['orderID'] = order_id
                flash(f"Order created successfully! Order ID: {order_id}", 'success')
                return redirect(url_for('dashboard'))

        return render_template('start_order.html')

    except pymysql.Error as e:
        conn.rollback()
        flash(f"Error creating order: {str(e)}", 'error')
        return render_template('start_order.html')
    finally:
        conn.close()



@app.route('/add-to-order', methods=['GET', 'POST'])
@staff_required
def add_to_order():
    conn = get_db()
    try:
        # Ensure orderID exists in the session
        if 'orderID' not in session:
            flash("Please start a new order before adding items.", "error")
            return redirect(url_for('start_order'))

        with conn.cursor() as cursor:
            # Fetch categories for dropdown
            cursor.execute("SELECT DISTINCT mainCategory FROM Category")
            categories = [row['mainCategory'] for row in cursor.fetchall()] or []

        # Initialize variables for rendering
        selected_category = None
        selected_subcategory = None
        items = None
        subcategories = []

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'find_items':
                # Fetch selected category and subcategory
                selected_category = request.form.get('category')
                selected_subcategory = request.form.get('subcategory')

                # Validate category-subcategory relationship
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 1 
                        FROM Category
                        WHERE mainCategory = %s AND subCategory = %s
                        LIMIT 1
                        """,
                        (selected_category, selected_subcategory)
                    )
                    combination_exists = cursor.fetchone()

                if not combination_exists:
                    flash(f"The combination of Category '{selected_category}' and Subcategory '{selected_subcategory}' does not exist.", "error")
                    return render_template(
                        'add_to_order.html',
                        categories=categories,
                        subcategories=[],
                        items=None,
                        selected_category=selected_category,
                        selected_subcategory=selected_subcategory
                    )

                # Fetch items for the category and subcategory, excluding items already in any order
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT i.ItemID, i.iDescription
                        FROM Item i
                        LEFT JOIN ItemIn ii ON i.ItemID = ii.ItemID
                        WHERE ii.orderID IS NULL
                        AND i.mainCategory = %s
                        AND i.subCategory = %s
                        """,
                        (selected_category, selected_subcategory)
                    )
                    items = cursor.fetchall()

                # Fetch subcategories for the selected category
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT subCategory 
                        FROM Category
                        WHERE mainCategory = %s
                        """,
                        (selected_category,)
                    )
                    subcategories = [row['subCategory'] for row in cursor.fetchall()]

                return render_template(
                    'add_to_order.html',
                    categories=categories,
                    subcategories=subcategories,
                    items=items,
                    selected_category=selected_category,
                    selected_subcategory=selected_subcategory
                )

            elif action == 'add_to_order':
                # Add selected item to the current order
                item_id = request.form.get('item_id')
                if not item_id:
                    flash('No item selected. Please select an item to add to the order.', "error")
                    return redirect(url_for('add_to_order'))

                with conn.cursor() as cursor:
                    # Check if the item is already in any order
                    cursor.execute(
                        """
                        SELECT ii.orderID 
                        FROM ItemIn ii 
                        WHERE ii.ItemID = %s
                        LIMIT 1
                        """,
                        (item_id,)
                    )
                    order_info = cursor.fetchone()

                    if order_info:
                        flash(f"Item {item_id} is already part of Order {order_info['orderID']} and cannot be added.", "error")
                        return redirect(url_for('add_to_order'))

                    # Insert the item into the current order
                    cursor.execute(
                        """
                        INSERT INTO ItemIn (orderID, ItemID)
                        VALUES (%s, %s)
                        """,
                        (session['orderID'], item_id)
                    )
                    conn.commit()

                flash(f"Item {item_id} added to order {session['orderID']} successfully!", "success")
                return redirect(url_for('dashboard'))

        # Render initial state
        return render_template('add_to_order.html', categories=categories, subcategories=subcategories, items=items)
    finally:
        conn.close()




# Update order status (Part 10) - Get data
@app.route('/get_order_details/<int:order_id>', methods=['GET'])
@login_required
def get_order_details(order_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT o.orderID, o.orderDate, o.orderNotes, o.supervisor,
                       pc.fname as ClientFName, pc.lname as ClientLName,
                       i.ItemID, i.iDescription, i.color, d.status as item_status,
                       d.userName as assigned_volunteer
                FROM Ordered o
                JOIN Person pc ON o.client = pc.userName
                LEFT JOIN ItemIn ii ON o.orderID = ii.orderID
                LEFT JOIN Item i ON ii.ItemID = i.ItemID
                LEFT JOIN Delivered d ON ii.ItemID = d.ItemID
                WHERE o.orderID = %s
                ORDER BY i.ItemID
            """, (order_id,))
            order_details = cursor.fetchall()
            
            # Filter items based on user role
            user_role = session.get('roles', [])
            username = session['username']
            updatable_items = []
            
            for item in order_details:
                if 'staff' in user_role:
                    updatable_items.append(item)
                elif 'volunteer' in user_role and item['assigned_volunteer'] == username:
                    updatable_items.append(item)
            
            return jsonify({
                'order_details': order_details,
                'updatable_items': updatable_items
            })
    finally:
        conn.close()

# Update order status (Part 10) - Update data
@app.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    if request.method == 'POST':
        order_id = request.form.get('orderID')
        item_updates = request.form.get('item_updates')  # JSON string of item updates
        username = session['username']
        
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                items = json.loads(item_updates)
                
                for item in items:
                    item_id = item['itemId']
                    new_status = item['status']
                    
                    # Check authorization
                    cursor.execute("""
                        SELECT 1 FROM Delivered 
                        WHERE ItemID = %s AND userName = %s
                        OR EXISTS (
                            SELECT 1 FROM Ordered 
                            WHERE orderID = %s AND supervisor = %s
                        )
                    """, (item_id, username, order_id, username))
                    
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE Delivered 
                            SET status = %s, date = CURRENT_DATE()
                            WHERE ItemID = %s
                        """, (new_status, item_id))
                
                conn.commit()
                return jsonify({'success': True})
                
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)})
        finally:
            conn.close()

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
                    SET p.roomNum = 4, p.shelfNum = 3, p.pNotes = 'Ready for delivery'
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


@app.route('/view_ranking', methods=['GET', 'POST'])
def view_ranking():
    if request.method == 'POST':
        rank_date = request.form.get('rank_date')
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            if rank_date:
                query = '''SELECT 
                                p.userName,
                                p.fname AS FirstName,
                                p.lname AS LastName,
                                COALESCE(COUNT(d.orderID), 0) AS DeliveryCount
                            FROM 
                                Person p
                            JOIN 
                                Act a ON p.userName = a.userName
                            LEFT JOIN 
                                Delivered d ON p.userName = d.userName
                            WHERE 
                                a.roleID = 'Volunteer' AND d.date >= %s
                            GROUP BY 
                                p.userName
                            ORDER BY 
                                DeliveryCount DESC;'''
                cursor.execute(query, (rank_date,))
                data = cursor.fetchall()
                if not data:
                    flash('No data found for the given date.', 'error')
                    return render_template('dashboard/view_ranking.html')
                
                return render_template('dashboard/view_ranking.html', volunteers=data)
            else:
                flash('Please enter a valid date.', 'error')
                return redirect('dashboard/view_ranking')
        finally:
            cursor.close()
            conn.close()
    else:
        return render_template('dashboard/view_ranking.html')
    



def validate_donor(conn, donor_id):
    """Validates if the user is a registered donor."""
    try:
        with conn.cursor() as cursor:
            # Check if the donor exists in the Person table
            cursor.execute("SELECT userName FROM Person WHERE userName = %s", (donor_id,))
            donor = cursor.fetchone()
            if not donor:
                return False, 'Donor ID does not exist.'

            # Check if the donor has the 'donor' role in the Act table
            cursor.execute("""
                SELECT roleID 
                FROM Act 
                WHERE userName = %s AND roleID = 'donor'
            """, (donor_id,))
            role = cursor.fetchone()
            if not role:
                return False, 'The user is not registered as a donor.'

        # If both checks pass, the donor is valid
        return True, 'Donor validated successfully.'
    except pymysql.Error as e:
        return False, f"Database error: {str(e)}"


@app.route('/accept-donations', methods=['GET', 'POST'])
@staff_required
def accept_donations():
    conn = get_db()
    try:
        if request.method == 'POST':
            # Retrieve donor ID from the form
            donor_id = request.form.get('donor_id')

            # Validate donor
            is_valid, message = validate_donor(conn, donor_id)
            if not is_valid:
                flash(message, 'error')  # Flash error message
                return render_template('accept_donations.html')

            # Donor is valid, proceed with an alert and redirect
            add_donation_url = url_for('add_donation_details', donor_id=donor_id)
            return render_template(
                'accept_donations.html',
                success_redirect=True,
                success_message=message,
                add_donation_url=add_donation_url
            )

        # Render the accept donations page
        return render_template('accept_donations.html')

    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')
        return render_template('accept_donations.html')

    finally:
        conn.close()


@app.route('/add-donation-details/<donor_id>', methods=['GET', 'POST'])
@staff_required
def add_donation_details(donor_id):
    conn = get_db()
    captured_data = []  # To store captured ItemIDs and donor details
    try:
        if request.method == 'POST':
            i_descriptions = request.form.getlist('iDescriptions[]')
            main_categories = request.form.getlist('mainCategories[]')
            sub_categories = request.form.getlist('subCategories[]')
            colors = request.form.getlist('colors[]')
            is_news = request.form.getlist('isNews[]')
            has_pieces_list = request.form.getlist('hasPieces[]')
            materials = request.form.getlist('materials[]')

            with conn.cursor() as cursor:
                # Fetch donor name for capturing details
                cursor.execute("""
                    SELECT CONCAT(fname, ' ', lname) AS fullName FROM Person WHERE userName = %s
                """, (donor_id,))
                donor_name = cursor.fetchone()['fullName']

                for idx, description in enumerate(i_descriptions):
                    # Validate category combination
                    cursor.execute("""
                        SELECT 1 FROM Category WHERE mainCategory = %s AND subCategory = %s
                    """, (main_categories[idx], sub_categories[idx]))
                    category_exists = cursor.fetchone()
                    if not category_exists:
                        raise ValueError(f"Invalid category combination: {main_categories[idx]}, {sub_categories[idx]}")

                    # Insert the item into the Item table
                    cursor.execute("""
                        INSERT INTO Item (iDescription, color, isNew, hasPieces, material, mainCategory, subCategory)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (description, colors[idx], is_news[idx] == 'true', has_pieces_list[idx] == 'true', materials[idx], main_categories[idx], sub_categories[idx]))
                    conn.commit()

                    # Retrieve the generated ItemID
                    cursor.execute("SELECT LAST_INSERT_ID() AS ItemID")
                    item_id = cursor.fetchone()['ItemID']

                    # Link the item to the donor in the DonatedBy table
                    cursor.execute("""
                        INSERT INTO DonatedBy (ItemID, userName, donateDate)
                        VALUES (%s, %s, NOW())
                    """, (item_id, donor_id))
                    conn.commit()

                    # Add captured data to the list
                    captured_data.append({
                        'item_id': item_id,
                        'donor_name': donor_name,
                        'description': description
                    })

                    # Handle pieces if the item has pieces
                    if has_pieces_list[idx] == 'true':
                        piece_descriptions = request.form.getlist(f'pieceDescriptions_{idx + 1}[]')
                        lengths = request.form.getlist(f'lengths_{idx + 1}[]')
                        widths = request.form.getlist(f'widths_{idx + 1}[]')
                        heights = request.form.getlist(f'heights_{idx + 1}[]')
                        room_nums = request.form.getlist(f'roomNums_{idx + 1}[]')
                        shelf_nums = request.form.getlist(f'shelfNums_{idx + 1}[]')
                        p_notes = request.form.getlist(f'pNotes_{idx + 1}[]')

                        for j, p_description in enumerate(piece_descriptions):
                            # Check if the location exists in the Location table
                            cursor.execute("""
                                SELECT 1 FROM Location WHERE roomNum = %s AND shelfNum = %s
                            """, (room_nums[j], shelf_nums[j]))
                            location_exists = cursor.fetchone()

                            # Insert location if it doesn't exist
                            if not location_exists:
                                cursor.execute("""
                                    INSERT INTO Location (roomNum, shelfNum, shelf, shelfDescription)
                                    VALUES (%s, %s, %s, %s)
                                """, (room_nums[j], shelf_nums[j], f"Shelf-{shelf_nums[j]}", "Auto-created location"))
                                conn.commit()

                            # Insert the piece into the Piece table
                            cursor.execute("""
                                INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (item_id, j + 1, p_description, lengths[j], widths[j], heights[j], room_nums[j], shelf_nums[j], p_notes[j]))
                        conn.commit()

            # Pass captured data to the frontend
            return jsonify({
                'success': True,
                'message': 'All items and pieces recorded successfully!',
                'donor_name': donor_name,
                'captured_items': captured_data
            })

        # Fetch dropdown data for the form
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT mainCategory FROM Category")
            categories = [row['mainCategory'] for row in cursor.fetchall()]
            cursor.execute("SELECT DISTINCT subCategory FROM Category")
            subcategories = [row['subCategory'] for row in cursor.fetchall()]

        return render_template('add_donation_details.html', donor_id=donor_id, categories=categories, subcategories=subcategories)

    except pymysql.Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f"Error: {str(e)}"}), 500
    except ValueError as ve:
        return jsonify({'success': False, 'message': str(ve)}), 400
    finally:
        conn.close()



@app.route('/get-subcategories', methods=['POST'])
def get_subcategories():
    """Fetch subcategories based on selected main category."""
    conn = get_db()
    try:
        main_category = request.json.get('mainCategory')
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT subCategory FROM Category WHERE mainCategory = %s
            """, (main_category,))
            subcategories = [row['subCategory'] for row in cursor.fetchall()]
        return jsonify(subcategories=subcategories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    # app.run( debug = True)
    # app.run('127.0.0.1', 5000, debug = True)
    app.run('127.0.0.1', 5000, debug = True)
     