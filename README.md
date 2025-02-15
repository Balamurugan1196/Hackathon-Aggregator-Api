# Hackathon-Aggregator-Api


**📌 Project Overview**

Hackathon Aggregator API is a Flask-based API that provides real-time data on upcoming hackathons. It scrapes fresh data daily from the Devpost website using a custom web scraper and updates the database automatically. The scraper runs as a scheduled GitHub Action, ensuring that the data remains up to date. The API allows users to fetch, search, and filter hackathons based on various parameters such as date, mode, location, and prize money


**🛠 Features**

✅ Scrapes hackathon data automatically every day

✅ Stores data in MongoDB for efficient querying

✅ Provides API endpoints for fetching and filtering hackathons


**📂 Endpoints**

🔍 GET /hackathons - Retrieve all hackathons

🎯 GET /hackathons/search?name=xyz - Search for a hackathon by name

🏆 GET /hackathons/filter?params - Filter hackathons by date, mode, location, or prize

🚀 Deployment

This API is deployed using Render and updates daily via GitHub Actions.


**🏗 Tech Stack**

Python (Flask) 🐍

MongoDB 🍃

Selenium & BeautifulSoup 🌐

GitHub Actions ⚡



**📜 License**

This project is licensed under the MIT License.
