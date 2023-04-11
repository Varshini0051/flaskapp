from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import hashlib

app = Flask(__name__)
app.secret_key = "mysecretkey"

@app.route("/")
def index():
    return render_template("register.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = psycopg2.connect(
            host="localhost",
            database="mydatabase",
            user="postgres",
            password="Naamujaanu!23",
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = psycopg2.connect(
            host="localhost",
            database="mydatabase",
            user="postgres",
            password="Naamujaanu!23",
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, hashed_password),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            return redirect("/")
    else:
        return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        conn = psycopg2.connect(
            host="localhost",
            database="mydatabase",
            user="postgres",
            password="Naamujaanu!23",
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT username, email FROM users WHERE id=%s",
            (session["user_id"],),
        )
        user_data = cur.fetchone()
        cur.close()
        conn.close()

    
        user_dict = {"username": user_data[0], "email": user_data[1]}
        return jsonify(user_dict)
        # return render_template("dashboard.html")
    else:
        return redirect("/")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")
if __name__ == '__main__':
    app.run(debug=True)
