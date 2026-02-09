from flask import Flask, render_template, request, redirect, session
from flask import send_file
from db import get_connection
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
import io

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

    # GET request
    if request.method == "GET":
        cur.execute("SELECT * FROM buses WHERE bus_id=%s", (bus_id,))
        bus = cur.fetchone()
        cur.close()
        conn.close()
        return render_template("book.html", bus=bus)

    # POST request
    seats = int(request.form["seats"])
    user_id = session["user_id"]

    cur.execute("SELECT price FROM buses WHERE bus_id=%s", (bus_id,))
    price_data = cur.fetchone()

    if not price_data:
        return "Bus not found"

    price = price_data[0]
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

    return render_template("success.html", booking_id=booking_id)


# ======================
# GENERATE PASS
# ======================
def generate_pass(booking_id, total):

    # Generate QR in memory
    qr = qrcode.make(f"Booking ID: {booking_id}")
    qr_bytes = io.BytesIO()
    qr.save(qr_bytes)
    qr_bytes.seek(0)

    # Generate PDF in memory
    pdf_bytes = io.BytesIO()
    c = canvas.Canvas(pdf_bytes)

    c.drawString(100, 750, "Cloud Bus Pass")
    c.drawString(100, 730, f"Booking ID: {booking_id}")
    c.drawString(100, 710, f"Total Amount: ₹{total}")

    # Save QR temporarily inside PDF
    qr_image = qrcode.make(f"Booking ID: {booking_id}")
    qr_path = io.BytesIO()
    qr_image.save(qr_path)
    qr_path.seek(0)

    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(qr_path), 100, 580, width=120, height=120)

    c.save()
    pdf_bytes.seek(0)

    return send_file(
        pdf_bytes,
        as_attachment=True,
        download_name=f"bus_pass_{booking_id}.pdf",
        mimetype="application/pdf"
    )



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
