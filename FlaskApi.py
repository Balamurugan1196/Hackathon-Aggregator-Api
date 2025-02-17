from flask import Flask, jsonify, request
from pymongo import MongoClient
import os
import urllib.parse  


app = Flask(__name__)

# ✅ Get MongoDB credentials from environment variables
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))


if not username or not password:
    raise ValueError("❌ MongoDB credentials are missing. Set MONGO_USER and MONGO_PASS.")

mongodb_url = f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb"

# ✅ Connect to MongoDB Atlas
try:
    client = MongoClient(mongodb_url)
    db = client["hackathonDB"]
    collection = db["events"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    raise Exception(f"❌ MongoDB Connection Failed: {str(e)}")

# ✅ Health Check Route
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "running"}), 200

# ✅ Route: Get All Hackathons
@app.route('/hackathons', methods=['GET'])
def get_hackathons():
    hackathons = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB ID
    return jsonify(hackathons)

# ✅ Route: Search Hackathon by Name
@app.route('/hackathons/search', methods=['GET'])
def search_hackathons():
    query = request.args.get('name', '')
    results = list(collection.find({"name": {"$regex": query, "$options": "i"}}, {"_id": 0}))
    return jsonify(results)

# ✅ Route: Filter Hackathons (Date, Mode, Location, Prize)
@app.route('/hackathons/filter', methods=['GET'])
def filter_hackathons():
    filters = {}
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    mode = request.args.get('mode')
    location = request.args.get('location')
    min_prize = request.args.get('min_prize')

    if start_date:
        filters["start_date"] = {"$gte": start_date}
    if end_date:
        filters["end_date"] = {"$lte": end_date}
    if mode:
        filters["mode"] = mode
    if location:
        filters["location"] = location

    if min_prize:
        try:
            if min_prize.startswith(">="):
                filters["prize_money"] = {"$gte": int(min_prize[2:].strip())}
            elif min_prize.startswith("<="):
                filters["prize_money"] = {"$lte": int(min_prize[2:].strip())}
            elif min_prize.startswith(">"):
                filters["prize_money"] = {"$gt": int(min_prize[1:].strip())}
            elif min_prize.startswith("<"):
                filters["prize_money"] = {"$lt": int(min_prize[1:].strip())}
            else:
                return jsonify({"error": "Invalid min_prize query format"}), 400
        except ValueError:
            return jsonify({"error": "Invalid min_prize value"}), 400

    results = list(collection.find(filters, {"_id": 0}))
    return jsonify(results)

# ✅ Run Flask App on Render or Local
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Default to port 10000 if not set
    app.run(host='0.0.0.0', port=port)
