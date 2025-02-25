import os
import re
import time
import logging
import traceback
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load MongoDB credentials from environment variables
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))

# Connect to MongoDB Atlas
try:
    client = MongoClient(
        f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb",
        serverSelectionTimeoutMS=5000  # Timeout for connection
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

# Function to scroll the page gradually
def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, 300);")  # Smaller scroll increments
        time.sleep(1)  # Allow time for loading
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# Chrome WebDriver Setup
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in background
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")  # Set window size

# Automatically download and use the correct ChromeDriver version
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # MLH Hackathon Page
    url = "https://mlh.io/seasons/2025/events"
    driver.get(url)
    logging.info(f"🌐 Opened MLH page: {url}")

    # Scroll down to load all elements
    scroll_page(driver)
    logging.info("🖱️ Scrolled page to load all events.")

    hackathons_list = []
    time.sleep(3)
    WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CLASS_NAME, "container feature"))
)


    # Find all container elements
    feature_containers = driver.find_elements(By.CLASS_NAME, "container feature")
    if feature_containers:
        logging.info(f"✅ Found {len(feature_containers)} containers.")
    else:
        logging.warning("⚠️ No containers found on the page.")

    for container in feature_containers:
        try:
            row = container.find_element(By.CLASS_NAME, "row")
            event_wrappers = row.find_elements(By.CLASS_NAME, "event-wrapper")

            if event_wrappers:
                logging.info(f"✅ Found {len(event_wrappers)} upcoming events.")

                # Extract data from each event
                for event in event_wrappers:
                    try:
                        name = event.find_element(By.CLASS_NAME, "event-name").text.strip()
                        date_text = event.find_element(By.CLASS_NAME, "event-date").text.strip()
                        location = event.find_element(By.CLASS_NAME, "event-location").text.strip()
                        website = event.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        # Handle missing mode information
                        try:
                            mode = event.find_element(By.CLASS_NAME, "event-hybrid-notes").text.strip()
                        except:
                            mode = "Unknown"

                        # Adjust mode and location based on digital/physical
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
                        logging.error(f"Error extracting event data: {traceback.format_exc()}")

        except Exception as e:
            logging.error(f"Error processing container: {traceback.format_exc()}")

    # MongoDB insertion logic
    if hackathons_list:
        for event in hackathons_list:
            if not collection.find_one({"name": event["name"], "start_date": event["start_date"]}):
                collection.insert_one(event)
        logging.info("Inserted %d events into MongoDB.", len(hackathons_list))
    else:
        logging.warning("No events found to insert.")

except Exception as e:
    logging.error(f"An error occurred: {traceback.format_exc()}")

finally:
    driver.quit()
    logging.info("WebDriver closed.")