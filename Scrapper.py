from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import time  
import re
import os
import urllib.parse

# MongoDB Credentials
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))
client = MongoClient(f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb")
db = client["hackathonDB"]
collection = db["events"]
collection.delete_many({})  # Clear old data

# Chrome WebDriver Setup
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://devpost.com/hackathons")

# Ensure initial content loads
WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "hackathon-tile")))

# Dynamic Scrolling to Load More Hackathons
TARGET_COUNT = 50  # Change to 100 if needed
scroll_attempts, max_attempts = 0, 50
prev_count = 0

while True:
    events = driver.find_elements(By.CLASS_NAME, "hackathon-tile")
    current_count = len(events)

    if current_count >= TARGET_COUNT:
        print(f"✅ Loaded {current_count} hackathons. Stopping scroll.")
        break  # Stop scrolling once we have enough hackathons

    if current_count == prev_count:
        scroll_attempts += 1
        if scroll_attempts >= max_attempts:
            print("⚠️ Reached max scroll attempts. Stopping.")
            break  # Prevent infinite loop

    prev_count = current_count

    # Scroll to the last loaded hackathon to trigger lazy loading
    driver.execute_script("arguments[0].scrollIntoView();", events[-1])
    time.sleep(3)  # Allow time for new hackathons to load

    print(f"🔄 Scroll Attempt {scroll_attempts}: Found {current_count} hackathons.")

# Scraping Data
scraped_events = []
for event in events[:TARGET_COUNT]:
    try:
        driver.execute_script("arguments[0].scrollIntoView();", event)
        time.sleep(1)
        name = event.find_element(By.CSS_SELECTOR, "h3.mb-4").text
        date_text = event.find_element(By.CLASS_NAME, "submission-period").text  

        # Extract Start & End Dates
        date_match = re.search(r"(\w+ \d{1,2})(?:, (\d{4}))? - (\w+ \d{1,2}, \d{4})", date_text)
        if date_match:
            start_date, start_year, end_date = date_match.groups()
            if not start_year:
                start_date += f", {end_date.split()[-1]}"  # Add missing year
        else:
            start_date, end_date = date_text, "Not available"

        # Extract Mode & Location
        location_info = event.find_element(By.CLASS_NAME, "info").text
        mode = "Online" if "online" in location_info.lower() else "Offline"
        location = "None" if mode == "Online" else location_info

        # Extract Prize Money
        try:
            prize = event.find_element(By.CLASS_NAME, "prize-amount").text
        except:
            prize = "Not mentioned"

        # Extract Apply Link
        apply_link = event.find_element(By.TAG_NAME, "a").get_attribute("href")

        scraped_events.append({
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "mode": mode,
            "location": location,
            "prize_money": prize,
            "apply_link": apply_link
        })
    except Exception as e:
        print(f"Skipping one event due to error: {e}")

# Insert Data into MongoDB
if scraped_events:
    collection.insert_many(scraped_events)
    print(f"{len(scraped_events)} hackathons stored in MongoDB successfully!")

driver.quit()
