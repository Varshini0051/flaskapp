from flask import Flask, request, redirect, session, jsonify,g
import psycopg2
import hashlib

app = Flask(__name__)
app.secret_key = "mysecretkey"

DATABASE = {
    'host': 'localhost',
    'database': 'mydatabase',
    'user': 'postgres',
    'password': 'Naamujaanu!23'
}
def get_db():
   
    if 'db' not in g:
        g.db = psycopg2.connect(
            host=DATABASE['host'],
            database=DATABASE['database'],
            user=DATABASE['user'],
            password=DATABASE['password']
        )
    return g.db
@app.teardown_appcontext
def close_db(error):
   
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route("/")


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        get_data=request.get_json()
        username = get_data["username"]
        email = get_data["email"]
        password = get_data["password"]
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password),
        )
        db.commit()
        cur.close()
        db.close()

        if get_data is not None:
            return jsonify({"success": True, "message": "Registration successful"})
        else:
            return jsonify({"success": False, "message": "Invalid email or password"})
    else:
        return jsonify({"message": "Method not allowed"}), 405

@app.route("/login", methods=["GET","POST"])
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
        session["user_id"] = user[0]
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid email or password"})

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
        # return render_template("dashboard.html")
    else:
        return redirect("/")
@app.route('/users', methods=["GET", "POST"])
def get_users():
    db = get_db()
    cur = db.cursor()

    cur.execute('SELECT * FROM users')
    rows = cur.fetchall()

    cur.close()
    db.close()
    users=[]
    for row in rows:
        user={"id":row[0],"username":row[1],"email":row[2]}
        users.append(user)
    if rows is not None:
        return jsonify(users)
    else:
        return jsonify({"message": "Users is empty"}), 404



@app.route('/users/<int:user_id>', methods=["GET", "POST","PATCH"])
def get_user(user_id):
    db = get_db()
    cur = db.cursor()

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
