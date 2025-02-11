from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from pymongo import MongoClient
import time  
import re
import urllib.parse

# ✅ Encode MongoDB Credentials
username = urllib.parse.quote_plus("admin")  # Your MongoDB username
password = urllib.parse.quote_plus("Bala@9952")  # Your MongoDB password

# ✅ Connect to MongoDB Atlas
client = MongoClient(f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb")
db = client["hackathonDB"]
collection = db["events"]

# ✅ Clear existing data to avoid duplication
collection.delete_many({})  
print("Database cleared before inserting new data.")

# Path to your ChromeDriver
chrome_driver_path = r"C:\Users\BALA\Downloads\chromedriver\chromedriver.exe"

# Set up Chrome WebDriver service
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service)

# Open Devpost hackathon page
url = "https://devpost.com/hackathons"
driver.get(url)

# Wait for hackathons to load
time.sleep(8)

# Scrape hackathon details
events = driver.find_elements(By.CLASS_NAME, "hackathon-tile")

scraped_events = []

for event in events:
    name = event.find_element(By.CLASS_NAME, "mb-4").text
    date_text = event.find_element(By.CLASS_NAME, "submission-period").text  

    # Extract start_date and end_date with proper format handling
    date_match = re.search(r"(\w+ \d{1,2})(?:, (\d{4}))? - (\w+ \d{1,2}, \d{4})", date_text)
    if date_match:
        start_date, start_year, end_date = date_match.groups()
        if not start_year:
            start_date += f", {end_date.split()[-1]}"  # Add year if missing
    else:
        start_date, end_date = date_text, "Not available"

    # Extract mode & location
    location_info = event.find_element(By.CLASS_NAME, "info").text
    mode = "Online" if "online" in location_info.lower() else "Offline"
    location = "None" if mode == "Online" else location_info

    # Extract prize amount
    try:
        prize = event.find_element(By.CLASS_NAME, "prize-amount").text
    except:
        prize = "Not mentioned"

    # Extract apply link
    apply_link = event.find_element(By.TAG_NAME, "a").get_attribute("href")

    hackathon_data = {
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "mode": mode,
        "location": location,
        "prize_money": prize,
        "apply_link": apply_link
    }

    scraped_events.append(hackathon_data)

# Insert into MongoDB
if scraped_events:
    collection.insert_many(scraped_events)
    print(f"{len(scraped_events)} hackathons stored in MongoDB successfully!")

# Close browser
driver.quit()
