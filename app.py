from flask import Flask, render_template, request, redirect, session
from db import get_connection
import qrcode
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")


# ======================
# HOME
# ======================
@app.route("/")
def home():
    return render_template("index.html")


# ======================
# REGISTER
# ======================
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
        except Exception:
            conn.rollback()
            return "Email already registered."
        finally:
            cur.close()
            conn.close()

        return redirect("/login")

    return render_template("register.html")


# ======================
# LOGIN
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, role FROM users WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]

            if session["role"] == "admin":
                return redirect("/admin")

            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")


# ======================
# DASHBOARD
# ======================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM buses")
    buses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("dashboard.html", buses=buses)


# ======================
# ADMIN
# ======================
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/login")

    return render_template("admin.html")


# ======================
# ADD BUS
# ======================
@app.route("/add_bus", methods=["POST"])
def add_bus():
    if session.get("role") != "admin":
        return redirect("/login")

    name = request.form["bus_name"]
    source = request.form["source"]
    destination = request.form["destination"]
    price = request.form["price"]
    seats = request.form["seats"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO buses (bus_name, source, destination, price, total_seats)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, source, destination, price, seats))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin")


# ======================
# BOOK TICKET
# ======================
@app.route("/book/<int:bus_id>", methods=["GET", "POST"])
def book(bus_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        seats = int(request.form["seats"])
        user_id = session["user_id"]

        cur.execute("SELECT price FROM buses WHERE id=%s", (bus_id,))
        result = cur.fetchone()

        if not result:
            cur.close()
            conn.close()
            return "Bus not found"

        price = result[0]
        total = price * seats

        cur.execute("""
            INSERT INTO bookings(user_id, bus_id, seats, total_amount)
            VALUES(%s, %s, %s, %s)
            RETURNING booking_id
        """, (user_id, bus_id, seats, total))

        booking_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        generate_pass(booking_id)

        return render_template("success.html", booking_id=booking_id)

    cur.execute("SELECT * FROM buses WHERE id=%s", (bus_id,))
    bus = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("book.html", bus=bus)


# ======================
# GENERATE PASS
# ======================
def generate_pass(booking_id):
    os.makedirs("static", exist_ok=True)

    qr = qrcode.make(f"Booking ID: {booking_id}")
    qr_path = f"static/qr_{booking_id}.png"
    qr.save(qr_path)

    pdf_path = f"static/pass_{booking_id}.pdf"
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, "Cloud Bus Pass")
    c.drawString(100, 730, f"Booking ID: {booking_id}")
    c.drawImage(qr_path, 100, 600, width=100, height=100)
    c.save()


# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
