import os
import re
import time
import random
import logging
import traceback
import urllib.parse
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load MongoDB credentials
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))

# Connect to MongoDB Atlas
try:
    client = MongoClient(
        f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb",
        serverSelectionTimeoutMS=5000
    )
    client.server_info()  # Test connection
    db = client["hackathondb"]
    collection = db["events"]
    logging.info("✅ Connected to MongoDB.")
except Exception as e:
    logging.error(f"❌ Failed to connect to MongoDB: {e}")
    raise

# Function to parse MLH event dates
def parse_mlh_date(date_text):
    try:
        current_year = datetime.today().year
        date_text = re.sub(r"(ST|ND|RD|TH)", "", date_text, flags=re.IGNORECASE)
        date_pattern = r"([A-Za-z]+) (\d{1,2})\s*-\s*((?:[A-Za-z]+ )?\d{1,2})"
        match = re.match(date_pattern, date_text.strip())
        if match:
            start_month_name, start_day, end_part = match.groups()
            start_month_number = datetime.strptime(start_month_name[:3], "%b").month
            start_date = datetime(current_year, start_month_number, int(start_day)).strftime("%Y-%m-%d")
            end_match = re.match(r"([A-Za-z]+ )?(\d{1,2})", end_part.strip())
            if end_match:
                end_month_name, end_day = end_match.groups()
                end_month_number = datetime.strptime(end_month_name[:3], "%b").month if end_month_name else start_month_number
                end_date = datetime(current_year, end_month_number, int(end_day)).strftime("%Y-%m-%d")
            else:
                end_date = start_date
            return start_date, end_date
    except Exception as e:
        logging.error(f"Error parsing date: {date_text}, Error: {e}")
    return None, None

# Function to scroll gradually
def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(10):  # Multiple scrolls
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(random.uniform(2, 5))  # Randomized delay
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# Chrome WebDriver Setup with Stealth Mode
chrome_options = uc.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Evade detection
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
driver = uc.Chrome(options=chrome_options)

try:
    url = "https://mlh.io/seasons/2025/events"
    driver.get(url)
    logging.info(f"🌐 Opened MLH page: {url}")
    scroll_page(driver)
    logging.info("🖱️ Scrolled page to load all events.")
    time.sleep(3)
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "container.feature"))
    )
    feature_containers = driver.find_elements(By.CLASS_NAME, "container.feature")
    hackathons_list = []

    for container in feature_containers:
        try:
            row = container.find_element(By.CLASS_NAME, "row")
            event_wrappers = row.find_elements(By.CLASS_NAME, "event-wrapper")
            if event_wrappers:
                logging.info(f"✅ Found {len(event_wrappers)} upcoming events.")
                for event in event_wrappers:
                    try:
                        name = event.find_element(By.CLASS_NAME, "event-name").text.strip()
                        date_text = event.find_element(By.CLASS_NAME, "event-date").text.strip()
                        location = event.find_element(By.CLASS_NAME, "event-location").text.strip()
                        website = event.find_element(By.TAG_NAME, "a").get_attribute("href")
                        try:
                            mode = event.find_element(By.CLASS_NAME, "event-hybrid-notes").text.strip()
                        except:
                            mode = "Unknown"
                        if mode == "Digital Only":
                            mode = "Online"
                            location = "Everywhere"
                        else:
                            mode = "Offline"
                        start_date, end_date = parse_mlh_date(date_text)
                        event_data = {
                            "name": name,
                            "start_date": start_date,
                            "end_date": end_date,
                            "location": location,
                            "apply_link": website,
                            "mode": mode,
                            "source": "MLH"
                        }
                        hackathons_list.append(event_data)
                        logging.info(f"✔️ Event data extracted: {name}")
                    except Exception as e:
                        logging.error(f"❌ Error extracting event data: {traceback.format_exc()}")
                break
        except Exception as e:
            logging.warning(f"⚠️ Skipping container due to missing elements: {traceback.format_exc()}")

    if hackathons_list:
        for event in hackathons_list:
            if event["start_date"] and event["end_date"] and not collection.find_one({"name": event["name"], "start_date": event["start_date"]}):
                collection.insert_one(event)
        logging.info(f"✅ Inserted {len(hackathons_list)} events into MongoDB.")
    else:
        logging.warning("⚠️ No new events found to insert.")

except Exception as e:
    logging.error(f"❌ An error occurred: {traceback.format_exc()}")

finally:
    driver.quit()
    logging.info("🚪 WebDriver closed.")
