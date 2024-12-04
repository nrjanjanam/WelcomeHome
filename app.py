from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from functools import wraps
import os
from config import Config
from database import get_db, hash_password
import phonenumbers

app = Flask(__name__, static_url_path='/static')
app.config.from_object(Config)
app.secret_key = 'welcome home app 1'

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



if __name__ == '__main__':
    app.run(debug= True)
     