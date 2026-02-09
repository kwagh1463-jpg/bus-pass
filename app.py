from flask import Flask, render_template, request, redirect, session
from db import get_connection
import qrcode
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = "secretkey"


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
            cur.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """, (name, email, password))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return "Email already registered"
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
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[4] if len(user) > 4 else "user"

            if session["role"] == "admin":
                return redirect("/admin")

            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")


# ======================
# USER DASHBOARD
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
# ADMIN PAGE
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

    # GET REQUEST
    if request.method == "GET":
        cur.execute("SELECT * FROM buses WHERE bus_id=%s", (bus_id,))
        bus = cur.fetchone()
        cur.close()
        conn.close()

        if not bus:
            return "Bus not found"

        return render_template("book.html", bus=bus)

    # POST REQUEST
    seats_requested = int(request.form["seats"])
    user_id = session["user_id"]

    # Get bus details
    cur.execute("SELECT price, total_seats FROM buses WHERE bus_id=%s", (bus_id,))
    bus = cur.fetchone()

    if not bus:
        cur.close()
        conn.close()
        return "Bus not found"

    price, total_seats = bus

    # Check already booked seats
    cur.execute("SELECT COALESCE(SUM(seats),0) FROM bookings WHERE bus_id=%s", (bus_id,))
    booked = cur.fetchone()[0]

    available = total_seats - booked

    if seats_requested > available:
        cur.close()
        conn.close()
        return f"Only {available} seats available"

    total_amount = price * seats_requested

    cur.execute("""
        INSERT INTO bookings(user_id, bus_id, seats, total_amount)
        VALUES(%s, %s, %s, %s)
        RETURNING booking_id
    """, (user_id, bus_id, seats_requested, total_amount))

    booking_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    generate_pass(booking_id)

    return render_template("success.html", booking_id=booking_id)


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


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)
