# db.py
import mysql.connector
from config import db_config

def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Successfully connected to the database")
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return connection


def signup_user(username, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, email, password))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        print("Error:", err)
        return None
    finally:
        cursor.close()
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print("Error:", err)
        return None
    finally:
        cursor.close()
        conn.close()
