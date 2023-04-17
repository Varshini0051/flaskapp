from flask import Flask, request, redirect, session, jsonify,g
import re
import os
import psycopg2
from functools import wraps
import jwt
import hashlib
from dotenv import load_dotenv
from datetime import timedelta
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

load_dotenv()
url = os.getenv('url')
secret_key = os.getenv('secret_key')
jwt_secret_key= os.getenv('jwt_secret_key')

app = Flask(__name__)
app.secret_key = secret_key
app.config['JWT_SECRET_KEY'] = jwt_secret_key
jwt = JWTManager(app)




def get_db():
   
    if 'db' not in g:
        g.db = psycopg2.connect(
           url
        )
    return g.db
@app.teardown_appcontext
def close_db(error):
   
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data["username"]
    email = data["email"]
    password = data["password"]
    if not re.match(r'^[a-zA-Z0-9]{5,20}$', username):
        return jsonify({"success": False, "message": "Username is invalid"}), 401
    if not re.match(r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({"success": False, "message": "Email is invalid"}), 401
    if not re.match(r'^.{5,}$', password):
        return jsonify({"success": False, "message": "Password is invalid"}), 401

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    db = get_db()
    cur = db.cursor()

    # Check if username or email already exists in database
    cur.execute(
        "SELECT * FROM users WHERE username=%s OR email=%s",
        (username, email)
    )
    user = cur.fetchone()

    if user is not None:
        cur.close()
        db.close()
        return jsonify({"success": False, "message": "Username or email already exists"})

    # Insert data into database
    cur.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
        (username, email, hashed_password)
    )
    db.commit()

    cur.close()
    db.close()

    return jsonify({"success": True, "message": "Registration successful"})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data["email"]
    password = data["password"]
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, hashed_password),
    )
    user = cur.fetchone()
    cur.close()
    db.close()

    if user:
        # Generate and return JWT access token
        access_token = create_access_token(identity=user[0], expires_delta=timedelta(hours=1))
        return jsonify({"success": True, "access_token": access_token})
    else:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401
    # return jsonify("hi")
@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        db= get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT username, email FROM users WHERE id=%s",
            (session["user_id"],),
        )
        user_data = cur.fetchone()
        cur.close()
        db.close()

    
        user_dict = {"username": user_data[0], "email": user_data[1]}
        return jsonify(user_dict)
    else:
        return redirect("/")
@app.route('/users/<int:user_id>', methods=["GET","DELETE","PATCH"])
@jwt_required()
def user(user_id):
    if request.method == "GET":
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s",(user_id,))
        user = cur.fetchone()
        cur.close()
        db.close()
        if user:
            user_dict = {"id": user[0], "username": user[1], "email": user[2]}
            return jsonify(user_dict)
        else:
            return jsonify({"message": "User not found"}), 404
    elif request.method == "DELETE":
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "DELETE FROM users WHERE id=%s",
            (user_id,)
        )
        db.commit()
        cur.close()
        db.close()

        return jsonify({"message": "User deleted successfully"})
    elif request.method == "PATCH":
        db = get_db()
        cur = db.cursor()
        data = request.json
        username = data.get("username")
        email = data.get("email")
        # update the user details in the database
        cur.execute('UPDATE users SET username=%s, email=%s WHERE id=%s', (username, email, user_id))
        db.commit()

        # fetch the updated user details from the database
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        row = cur.fetchone()

        cur.close()
        db.close()

        if row is not None:
            user = {"id": row[0], "username": row[1], "email": row[2]}
            return jsonify(user)
        else:
            return jsonify({"message": "User not found"}), 404



@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")
if __name__ == '__main__':
    app.run(debug=True)
