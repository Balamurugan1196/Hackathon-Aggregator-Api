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

# ✅ Retrieve MongoDB credentials from GitHub Secrets
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))

# ✅ Connect to MongoDB Atlas
client = MongoClient(f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb")
db = client["hackathonDB"]
collection = db["events"]

# ✅ Clear existing data to avoid duplication
collection.delete_many({})
print("Database cleared before inserting new data.")

# ✅ Configure Chrome for GitHub Actions (Headless Mode)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# ✅ Set up Chrome WebDriver service (Use Default Path for Linux/Ubuntu)
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# ✅ Open Devpost hackathon page
url = "https://devpost.com/hackathons"
driver.get(url)

# ✅ Wait for initial hackathons to load using WebDriverWait
wait = WebDriverWait(driver, 30)
wait.until(EC.presence_of_element_located((By.CLASS_NAME, "hackathon-tile")))

# ✅ Scroll logic to load more hackathons
SCROLL_COUNT = 40  # Maximum number of scrolls
MIN_HACKATHONS = 50  # Target number of hackathons
SCROLL_PAUSE_TIME = 5  # Time to wait after each scroll

previous_count = 0  # Track number of events before scrolling

for _ in range(SCROLL_COUNT):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # ✅ Wait for new elements to load after scrolling
    time.sleep(SCROLL_PAUSE_TIME)  
    events = driver.find_elements(By.CLASS_NAME, "hackathon-tile")
    
    
    
    # ✅ If no new hackathons appear, stop scrolling
    
    
    

    # ✅ Stop if we reach the required number
    if len(events) >= MIN_HACKATHONS:
        break  

# ✅ Scrape hackathon details
scraped_events = []
for event in events:
    name = event.find_element(By.CSS_SELECTOR, "h3.mb-4").text
    date_text = event.find_element(By.CLASS_NAME, "submission-period").text  

    # ✅ Extract start_date and end_date with proper format handling
    date_match = re.search(r"(\w+ \d{1,2})(?:, (\d{4}))? - (\w+ \d{1,2}, \d{4})", date_text)
    if date_match:
        start_date, start_year, end_date = date_match.groups()
        if not start_year:
            start_date += f", {end_date.split()[-1]}"  # Add year if missing
    else:
        start_date, end_date = date_text, "Not available"

    # ✅ Extract mode & location
    location_info = event.find_element(By.CLASS_NAME, "info").text
    mode = "Online" if "online" in location_info.lower() else "Offline"
    location = "None" if mode == "Online" else location_info

    # ✅ Extract prize amount
    try:
        prize = event.find_element(By.CLASS_NAME, "prize-amount").text
    except:
        prize = "Not mentioned"

    # ✅ Extract apply link
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

# ✅ Insert into MongoDB
if scraped_events:
    collection.insert_many(scraped_events)
    print(f"{len(scraped_events)} hackathons stored in MongoDB successfully!")

# ✅ Close browser
driver.quit()
