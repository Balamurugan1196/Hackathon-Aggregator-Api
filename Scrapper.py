from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from datetime import datetime 
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
chrome_options.add_argument("--headless")  # Run in background
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service()  
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open Devpost Hackathons Page
driver.get("https://devpost.com/hackathons")

# Ensure Initial Content Loads
WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "hackathon-tile")))

# Dynamic Scrolling to Load More Hackathons
TARGET_COUNT = 100  # Adjust as needed
scroll_attempts, max_attempts = 0, 30
prev_count = 0

while True:
    events = driver.find_elements(By.CLASS_NAME, "hackathon-tile")
    current_count = len(events)

    if current_count >= TARGET_COUNT:
        print(f"✅ Loaded {current_count} hackathons. Stopping scroll.")
        break

    if current_count == prev_count:
        scroll_attempts += 1
        if scroll_attempts >= max_attempts:
            print("⚠️ No more hackathons found. Stopping.")
            break

    prev_count = current_count

    # Scroll Down using PAGE_DOWN multiple times before scrolling into view
    for _ in range(3):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(1)

    if events:
        driver.execute_script("arguments[0].scrollIntoView();", events[-1])

    time.sleep(3)  # Allow time for new hackathons to load

    print(f"🔄 Scroll Attempt {scroll_attempts}: Found {current_count} hackathons.")

# Refined Function to Extract Dates
def extract_dates(date_text):
    """
    Extracts start and end dates from multiple formats:
    - "Jan 31 - Mar 02, 2025"
    - "Feb 01 - 26, 2025"
    - "Dec 18, 2024 - Mar 02, 2025"
    - "Mar 02, 2025"
    Returns dates in ISO format (YYYY-MM-DD).
    """

    # If the date is "Not available", return the same
    if "Not available" in date_text:
        return "Not available", "Not available"

    current_year = datetime.now().year  # To infer missing years

    # Case 1: Match "Jan 31 - Mar 02, 2025"
    date_match = re.match(r"(\w{3} \d{1,2}) - (\w{3} \d{1,2}), (\d{4})", date_text)
    if date_match:
        start_day_month, end_day_month, year = date_match.groups()
        start_date = datetime.strptime(f"{start_day_month} {year}", "%b %d %Y")
        end_date = datetime.strptime(f"{end_day_month} {year}", "%b %d %Y")
        return start_date.date().isoformat(), end_date.date().isoformat()

    # Case 2: Match "Feb 01 - 26, 2025" or "Feb 01 - 26"
    date_match = re.match(r"(\w{3} \d{1,2}) - (\d{1,2}), (\d{4})", date_text)
    if date_match:
        start_day_month, end_day, year = date_match.groups()
        start_date = datetime.strptime(f"{start_day_month} {year}", "%b %d %Y")
        end_date = datetime.strptime(f"{start_day_month[:3]} {end_day} {year}", "%b %d %Y")
        return start_date.date().isoformat(), end_date.date().isoformat()

    # Case 3: Match "Dec 18, 2024 - Mar 02, 2025"
    date_match = re.match(r"(\w{3} \d{1,2}, \d{4}) - (\w{3} \d{1,2}, \d{4})", date_text)
    if date_match:
        start_date_str, end_date_str = date_match.groups()
        start_date = datetime.strptime(start_date_str, "%b %d, %Y")
        end_date = datetime.strptime(end_date_str, "%b %d, %Y")
        return start_date.date().isoformat(), end_date.date().isoformat()

    # Case 4: Match a single date, "Mar 02, 2025"
    date_match = re.match(r"(\w{3} \d{1,2}, \d{4})", date_text)
    if date_match:
        start_date_str = date_match.group(1)
        start_date = datetime.strptime(start_date_str, "%b %d, %Y")
        return start_date.date().isoformat(), start_date.date().isoformat()

    # If none of the formats match, return "Not available"
    return "Not available", "Not available"



# Refined Function to Extract Prize Money
def extract_prize_money(event):
    """
    Extracts prize money from a hackathon event.

    Parameters:
        event (WebElement): The Selenium WebElement containing hackathon details.

    Returns:
        int: The prize amount in integer format. Returns 0 if no valid prize is found.
    """
    try:
        prize_text = event.find_element(By.CLASS_NAME, "prize-amount").text.strip()
        prize_text = prize_text.lower().replace(",", "").replace("usd", "").strip()

        # Handle prize ranges (e.g., "Between $5K and $10K")
        range_match = re.findall(r'(\d+(\.\d+)?)([km]?)', prize_text)
        if range_match:
            amounts = []
            for num, _, suffix in range_match:
                num = float(num)
                if suffix == "k":
                    num *= 1000
                elif suffix == "m":
                    num *= 1_000_000
                amounts.append(int(num))
            return max(amounts)  # Return the highest prize in the range

        # Handle single prize cases (e.g., "$10K", "5M")
        match = re.search(r'(\d+(\.\d+)?)([km]?)', prize_text)
        if match:
            amount = float(match.group(1))
            suffix = match.group(3)
            if suffix == "k":
                amount *= 1000
            elif suffix == "m":
                amount *= 1_000_000
            return int(amount)

        return 0  # No valid prize found

    except Exception:
        return 0  # Return 0 if prize money is not mentioned

# Scraping Data
scraped_events = []
for event in events[:TARGET_COUNT]:
    try:
        driver.execute_script("arguments[0].scrollIntoView();", event)
        time.sleep(1)
        name = event.find_element(By.CSS_SELECTOR, "h3.mb-4").text
        date_text = event.find_element(By.CLASS_NAME, "submission-period").text  
        start_date, end_date = extract_dates(date_text)

        # Extract Mode & Location
        location_info = event.find_element(By.CLASS_NAME, "info").text
        mode = "Online" if "online" in location_info.lower() else "Offline"
        location = "None" if mode == "Online" else location_info

        # Extract Prize Money
        prize = extract_prize_money(event)

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
    print(f"{len(scraped_events)} hackathons stored in MongoDB successfully! 🚀")

driver.quit()
