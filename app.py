
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, EmailField
from wtforms.validators import DataRequired, Email
import cv2
import os
import time
from datetime import datetime
from flask import send_file

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Enable CSRF protection
csrf = CSRFProtect(app)

# Configure MySQL connection
db_config = {
    'host': 'localhost',
    'user': 'root',
    'port': '3306',
    'password': '20052020',  # Replace with your MySQL root password
    'database': 'autism_detection'
}

# Configure Flask-Mail for sending emails
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'nancy2005nov@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'ntgo jlmo jffs geml'  # Replace with your email password
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Serializer for generating password reset tokens
s = URLSafeTimedSerializer(app.secret_key)

# Establish database connection
def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Connection to MySQL database was successful!")
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None  # Return None if connection fails
    return connection
@app.route('/round1')
def round1():
    return render_template('round1.html')
@app.route('/autism')
def autism():
    return render_template('autism.html')

@app.route('/round2')
def round2():
    return render_template('round2.html')

results = {}
@app.route('/submit_times', methods=['POST'])
@csrf.exempt
def submit_times():
    data = request.json
    round_name = data.get('round')
    image1_time = data.get('image1_time', 0)
    image2_time = data.get('image2_time', 0)

    result = "non-autistic"
    if image1_time > image2_time:
        result = "autistic"

    results[round_name] = {
        "image1_time": image1_time,
        "image2_time": image2_time,
        "result": result
    }

    return jsonify({"status": "success", "result": result})

@app.route('/result')
@csrf.exempt
def result():
    round1_result = results['round1']['result']
    round2_result = results['round2']['result']

    if round1_result == "autistic" and round2_result == "autistic":
        final_result = "High Possibility of Autism"
    elif round1_result == "autistic" or round2_result == "autistic":
        final_result = "Low Possibility of Autism"
    else:
        final_result = "No Possibility of Autism"

    return render_template('result.html', final_result=final_result)

@app.route('/')
def home():
    return render_template('home.html')

# Route for signup
class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        hashed_password = generate_password_hash(password)  # Hash the password

        # Check if user already exists
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed. Please try again later.")
            return redirect(url_for('home'))

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Username or email already exists. Please choose a different one.")
            cursor.close()
            connection.close()
            return redirect(url_for('signup'))

        # Insert new user into the database with the hashed password
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
        connection.commit()
        cursor.close()
        connection.close()

        session['username'] = username
        flash("Signup successful!")
        return redirect(url_for('home'))  # Redirect to home page

    return render_template('signup.html', form=form)

# Route for login
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Retrieve user from the database
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed. Please try again later.")
            return redirect(url_for('home'))

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND email = %s", (username, email))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        # Check if the user exists and if the password is correct
        if user:
            stored_hash = user[3]  # Assuming 'password' is the 4th column (index 3) in the 'users' table

            if check_password_hash(stored_hash, password):  # Check if the hashed password matches
                session['username'] = username  # Store username in session
                flash("Login successful!")
                return redirect(url_for('home'))  # Redirect to home page
            else:
                flash("Invalid password.")
                return redirect(url_for('login'))
        else:
            flash("Username or email not found. Please sign up first.")
            return redirect(url_for('signup'))

    return render_template('login.html', form=form)

# Route for logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.")
    return redirect(url_for('home'))

# Forgot Password Form
class ForgotPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        email = form.email.data

        # Check if email exists in the database
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed. Please try again later.")
            return redirect(url_for('home'))

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            token = s.dumps(email, salt='email-confirm')
            reset_link = url_for('reset_password', token=token, _external=True)

            # Send reset email
            msg = Message('Password Reset Request', sender='nancy2005nov@gmail.com', recipients=[email])
            msg.body = f'Your password reset link is {reset_link}. This link is valid for 30 minutes.'
            mail.send(msg)

            flash("A password reset link has been sent to your email.")
            return redirect(url_for('login'))
        else:
            flash("Email not found.")
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html', form=form)

# Route for resetting password
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=1800)  # 30 minutes expiration
    except SignatureExpired:
        flash("The reset link is expired.")
        return redirect(url_for('forgot_password'))

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        password = form.password.data
        hashed_password = generate_password_hash(password)

        # Update password in the database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        connection.commit()
        cursor.close()
        connection.close()

        flash("Your password has been updated!")
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
