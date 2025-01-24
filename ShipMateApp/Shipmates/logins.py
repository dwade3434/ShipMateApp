from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from Shipmates import app

DB_CONFIG = {
    "database": "shipmates",
    "user": "postgres",
    "password": "aRiana#01",
    "host": "127.0.0.1",
    "port": "5432"
}

# Authentication check decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

# Function to get a database connection
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# Registration route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        address = request.form.get("address")
        address2 = request.form.get("address2")
        city = request.form.get("city")
        state = request.form.get("state")
        zipcode = request.form.get("zipcode")
        phone = request.form.get("phone")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if username already exists
                    cursor.execute("SELECT username FROM credentials WHERE username = %s", (username,))
                    result = cursor.fetchone()
                    
                    if result:
                        flash("Username already exists!", "error")
                        return redirect(url_for('register'))

                    # Hash the password before saving to the database
                    hashed_password = generate_password_hash(password)

                    cursor.execute("""
                        INSERT INTO credentials (username, password, address, address2, city, state, zipcode, phone)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (username, hashed_password, address, address2, city, state, zipcode, phone))
                    conn.commit()

                    flash("Registration successful! You can now log in.", "success")
                    return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {e}", "error")

    return render_template('register.html', title="Register")

# Login route
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if username exists
                    cursor.execute("SELECT password FROM credentials WHERE username = %s", (username,))
                    stored_password = cursor.fetchone()

                    if not stored_password:
                        return redirect(url_for('register'))
                    elif stored_password and check_password_hash(stored_password[0], password):
                        session['user_id'] = username  # Set user_id in session
                        flash("Login successful!", "success")
                        return redirect(url_for('create'))  
                    else:
                        flash("Invalid username or password", "error")

        except Exception as e:
            flash(f"Error: {e}", "error")

    return render_template('index.html', title="Login")

if __name__ == "__main__":
    app.run(debug=True)
