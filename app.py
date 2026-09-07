from flask import Flask, render_template, request, redirect, url_for
from database import get_connection, init_db
import qrcode, os

app = Flask(__name__)
init_db()  # make sure tables exist when the app starts

BASE_URL = "http://192.168.1.244:5000"  

# ---------- Admin: list + add events ----------
@app.route("/", methods=["GET", "POST"])
def admin_events():
    conn = get_connection()
    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        conn.execute("INSERT INTO events (name, date) VALUES (?, ?)", (name, date))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_events"))  # PRG: avoid resubmitting "Add Event" on refresh

    events = conn.execute("SELECT * FROM events").fetchall()
    conn.close()
    return render_template("admin_events.html", events=events)

# ---------- Admin: one event's dashboard ----------
@app.route("/event/<int:event_id>")
def event_detail(event_id):
    conn = get_connection()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    participants = conn.execute(
        "SELECT * FROM participants WHERE event_id = ?", (event_id,)
    ).fetchall()
    conn.close()

    qr_path = os.path.join("static", "qrcodes", f"event_{event_id}.png")
    if not os.path.exists(qr_path):
        generate_qr(event_id, BASE_URL)

    return render_template(
        "admin_event_detail.html",
        event=event,
        participants=participants,
        total_count=len(participants),
    )

def generate_qr(event_id, base_url):
    checkin_url = f"{base_url}/checkin/{event_id}"
    img = qrcode.make(checkin_url)
    folder = os.path.join("static", "qrcodes")
    os.makedirs(folder, exist_ok=True)
    img.save(os.path.join(folder, f"event_{event_id}.png"))

# ---------- Attendee: check-in form ----------
@app.route("/checkin/<int:event_id>", methods=["GET", "POST"])
def checkin(event_id):
    conn = get_connection()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if request.method == "POST":
        conn.execute(
            "INSERT INTO participants (event_id, name, mobile, email, company) VALUES (?, ?, ?, ?, ?)",
            (event_id, request.form["name"], request.form["mobile"],
             request.form["email"], request.form["company"]),
        )
        conn.commit()
        conn.close()
        # PRG: redirect to a plain GET page instead of returning content on the POST itself.
        # This means there is nothing left in browser history for Back+Refresh to resubmit.
        return redirect(url_for("checkin_success", event_id=event_id))

    conn.close()
    return render_template("checkin_form.html", event=event)

# ---------- Attendee: confirmation page (GET only, nothing to resubmit) ----------
@app.route("/checkin/<int:event_id>/success")
def checkin_success(event_id):
    conn = get_connection()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return render_template("checkin_success.html", event=event)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)