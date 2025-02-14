from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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

# Dynamic Scrolling
TARGET_COUNT = 50  # Change to 100 if needed
scroll_attempts, max_attempts = 0, 30
prev_count = 0

while len(driver.find_elements(By.CLASS_NAME, "hackathon-tile")) < TARGET_COUNT and scroll_attempts < max_attempts:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll to bottom
    time.sleep(3)  # Give time for content to load

    # Wait for new elements to appear
    WebDriverWait(driver, 5).until(
        lambda d: len(d.find_elements(By.CLASS_NAME, "hackathon-tile")) > prev_count
    )

    events = driver.find_elements(By.CLASS_NAME, "hackathon-tile")
    
    print(f"Scroll Attempt {scroll_attempts + 1}: Found {len(events)} hackathons")

    # Stop if no new hackathons loaded
    if len(events) == prev_count:
        break

    prev_count = len(events)
    scroll_attempts += 1

print(f"Total Hackathons Loaded: {len(events)}")

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
