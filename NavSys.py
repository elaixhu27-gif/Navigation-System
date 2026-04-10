from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
import os

app = Flask(__name__)

# INIT DATABASE
def init_db():
    conn = sqlite3.connect("navigation.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start TEXT,
        destination TEXT,
        distance REAL,
        duration REAL
    )
    """)
    conn.commit()
    conn.close()

# SAVE ROUTE
def save_route(start, destination, distance, duration):
    conn = sqlite3.connect("navigation.db")
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO routes (start, destination, distance, duration)
    VALUES (?, ?, ?, ?)
    """, (start, destination, distance, duration))
    conn.commit()
    conn.close()

# HOME PAGE
@app.route("/")
def home():
    return render_template("index.html")

# HISTORY
@app.route("/history")
def history():
    conn = sqlite3.connect("navigation.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM routes ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()
    return jsonify(data)

# ROUTE API
@app.route("/route", methods=["POST"])
def route():
    data = request.json
    start = data["start"]
    destination = data["destination"]

    # GEOCODING (OpenStreetMap)
    start_url = f"https://nominatim.openstreetmap.org/search?format=json&q={start}"
    end_url = f"https://nominatim.openstreetmap.org/search?format=json&q={destination}"

    start_data = requests.get(start_url, headers={"User-Agent": "Mozilla/5.0"}).json()
    end_data = requests.get(end_url, headers={"User-Agent": "Mozilla/5.0"}).json()

    if not start_data or not end_data:
        return jsonify({"error": "Location not found"}), 400

    start_lat, start_lon = start_data[0]["lat"], start_data[0]["lon"]
    end_lat, end_lon = end_data[0]["lat"], end_data[0]["lon"]

    # ROUTE (OSRM)
    route_url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    route_data = requests.get(route_url).json()

    route = route_data["routes"][0]
    distance = route["distance"] / 1000
    duration = route["duration"] / 60
    geometry = route["geometry"]

    # SAVE TO DATABASE
    save_route(start, destination, distance, duration)

    return jsonify({
        "distance": distance,
        "duration": duration,
        "geometry": geometry
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 27000))
    app.run(host="0.0.0.0", port=port)