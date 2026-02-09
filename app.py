import os
from flask import Flask, render_template, request, redirect, session
from db import get_connection

app = Flask(__name__)
app.secret_key = "supersecretkey"


# Home
@app.route("/")
def home():
    return render_template("index.html")


# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"Error: {e}"

        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user"] = user[1]
            return redirect("/dashboard")
        else:
            return "Invalid Credentials"

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return f"Welcome {session['user']}!"


if __name__ == "__main__":
    app.run(debug=True)
