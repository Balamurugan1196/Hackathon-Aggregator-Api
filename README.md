🚀 Hackathon-Aggregator-Api
📌 Project Overview
Hackathon Aggregator API is a Flask-based API that provides real-time data on upcoming hackathons.
It scrapes fresh data daily from the Devpost website using a custom web scraper and updates the database automatically.
The scraper runs as a scheduled GitHub Action, ensuring that the data remains up to date.

🔹 Fetch, search, and filter hackathons effortlessly
🔹 Automatically updates data every day via GitHub Actions
🔹 Provides easy-to-use API endpoints for querying hackathons

🔗 Live API: https://hackathon-aggregator-api.onrender.com

🛠 Features
✅ Automated Scraping – Hackathon data is scraped daily using Selenium & GitHub Actions
✅ Real-time Updates – The database is updated automatically, ensuring fresh data
✅ Powerful API – Retrieve, search, and filter hackathons based on multiple parameters
✅ Efficient Storage – Uses MongoDB for fast and scalable data retrieval

📂 API Endpoints
🔍 GET /hackathons – Retrieve all hackathons
🎯 GET /hackathons/search?name=xyz – Search for a hackathon by name
🏆 GET /hackathons/filter?params – Filter hackathons by date, mode, location, or prize

🚀 Deployment
This API is deployed using Render and automatically updates daily via GitHub Actions.

🏗 Tech Stack
🐍 Python (Flask) – Backend framework for handling API requests
🍃 MongoDB – NoSQL database for storing hackathon data
🌐 Selenium – Web scraping library for extracting hackathon details
⚡ GitHub Actions – Automates the daily scraping process

📜 License
This project is licensed under the MIT License.

