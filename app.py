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
        g.db = psycopg2.connect(url)
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

@app.route('/user_details/<int:user_id>', methods=["GET","PATCH"])
@jwt_required()
def user_details(user_id):
    #to search by user_id, username
    if request.method == "GET":
        db = get_db()
        cur = db.cursor()
        cur.execute("select role from users where id=%s",(user_id,))
        role= cur.fetchone()[0]
        #if user_id is employee display details and manager name
        if (role=="Employee"):
            cur.execute("SELECT u.id, u.username, u.email, u.role,u.task_assigned, m.manager_name FROM users u JOIN managers m ON u.manager_id = m.manager_id WHERE u.id = %s;",(user_id,))
            user = cur.fetchone()
            # cur.close()
            # db.close()
            if user:
                user_dict = {"id": user[0], "username": user[1], "email": user[2], "role": user[3],"assigned_task": user[4], "manager_name": user[5]}
                return jsonify(user_dict)
            else:
                return jsonify({"message": "User not found"}), 404
        #if user_id is manager display details of employees reporting to this manager
        elif(role=="Manager"):
            cur.execute("SELECT u.username FROM users u WHERE u.id=%s",(user_id,))
            manager_name= cur.fetchone()[0]
            cur.execute("SELECT   m.manager_name, u.id, u.username, u.email, u.role , u.task_assigned FROM managers m INNER JOIN users u ON m.manager_id = u.manager_id WHERE m.manager_name = %s",(manager_name,))
            users= cur.fetchall()
            user_list=[]
            if users:
                for user in users:
                    user_dict = {"employee_id": user[1], "manager_name":user[0], "username": user[2], "email": user[3], "role": user[4], "assigned_task": user[5]}
                    user_list.append(user_dict)
                return jsonify(user_list)
            else:
                return jsonify({"message": "User not found"}), 404
    
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
    return jsonify({"message": "Invalid request method"}), 405
   

@app.route('/add_user', methods=["POST"])
@jwt_required()
# define a function to add a new user
def add_user():
    current_user_id = get_jwt_identity()
    user_data = request.get_json()
    username = user_data["username"]
    email = user_data["email"]
    password = user_data["password"]
    user_role= user_data["user_role"]
    # user_role1= request.json.get('user_role1', None)
    manager_id = user_data["manager_id"]
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    cur = db.cursor()
    # check if the user adding the employee has admin role
    cur.execute("SELECT role FROM users WHERE id=%s",(current_user_id,))
    role = cur.fetchone()[0]
    if role != 'Admin':
        return jsonify({"message": "Only an Admin can add a new employee."}), 403
    
    # check if the role is valid
    if user_role not in ['Employee', 'Manager']:
        return jsonify ({"message": "Invalid role. Role should be either 'Employee' or 'Manager'."}), 403

    # # if the role is Manager, check if the manager_id is valid
    # if user_role == 'Manager':
    #     cur.execute("SELECT manager_id FROM managers WHERE manager_name =%s", (username,))
    #     manager_ids = [row[0] for row in cur.fetchall()]
    #     if manager_id not in manager_ids:
    #         return jsonify ({"message": "Invalid manager_id."})

    # add the new user
    cur.execute("INSERT INTO users (username, email, password, role, manager_id) VALUES (%s, %s, %s, %s, %s)", (username, email, hashed_password, user_role, manager_id))
    db.commit()
    cur.close()
    db.close()

    return jsonify ({"message": "New user added successfully."})

# define a function to change an employee's reporting manager
@app.route('/change_manager/<int:user_id>', methods=["PATCH"])
@jwt_required()
def change_manager(user_id):
    # check if the user adding the employee has admin role
    current_user_id = get_jwt_identity()
    new_manager_id = request.json.get('new_manager_id')
    db = get_db()
    cur = db.cursor()
    # check if the user adding the employee has admin role
    cur.execute("SELECT role FROM users WHERE id=%s",(current_user_id,))
    role = cur.fetchone()[0]
    if role != 'Admin':
        return jsonify({"message": "Only an Admin can change an employee's reporting manager."}), 403

    # check if the user_id and new_manager_id are valid
    cur.execute("SELECT manager_id FROM managers WHERE manager_id = %s", (new_manager_id,))
    if cur.fetchone() is None:
        return jsonify({"message": "Invalid manager_id."})
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if cur.fetchone() is None:
        return jsonify({"message": "Invalid user_id."})
    
    cur.execute("UPDATE users SET manager_id = %s WHERE id = %s", (new_manager_id, user_id))
    db.commit()
    cur.close()
    db.close()
    return jsonify ({"message":  "Reporting manager changed successfully."})

# define a function to change an employee's role
@app.route('/change_role/<int:user_id>', methods=["PATCH"])
@jwt_required()
def change_role(user_id):
    current_user_id = get_jwt_identity()
    new_role = request.json.get('new_role', None)
    db = get_db()
    cur = db.cursor()
    # check if the user adding the employee has admin role
    cur.execute("SELECT role FROM users WHERE id=%s",(current_user_id,))
    role = cur.fetchone()[0]
    if role != 'Admin':
        return jsonify({"message": "Only an Admin can change an employee's role."}), 403
    
    # check if the user_id and new_role are valid
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if cur.fetchone() is None:
        return jsonify ({"message": "Invalid user_id."})
    if new_role not in ['Employee', 'Manager']:
        return jsonify ({"message": "Invalid role. Role should be either 'Employee' or 'Manager'."})

    # change the role of the employee
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
    db.commit()
    cur.close()
    db.close()
    return jsonify ({"message": "Role changed successfully."})

@app.route('/assign_task/<int:user_id>', methods=["POST","PATCH"])
@jwt_required()
# define a function to add task to employee
def assign_task(user_id):
    current_user_id = get_jwt_identity()
    # task = request.get_json('task')
    task = request.json
    assigned_task = task.get("task")
    db = get_db()
    cur = db.cursor()
    # check if the user adding the employee has admin role
    cur.execute("SELECT role FROM users WHERE id=%s",(current_user_id,))
    role = cur.fetchone()[0]
    if role != 'Manager':
        return jsonify({"message": "Only a Manager can assign an employee's task."}), 403
    # assign task to a Employee
    cur.execute("UPDATE users SET task_assigned = %s WHERE id = %s;", (assigned_task,user_id))
    db.commit()
    cur.close()
    db.close()
    return jsonify ({"message": "Task assigned successfully."})

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")
if __name__ == '__main__':
    app.run(debug=True)
