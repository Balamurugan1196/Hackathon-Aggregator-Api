import os
import re
import time
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

# Load MongoDB credentials from environment variables
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))

# Connect to MongoDB Atlas
client = MongoClient(
    f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb"
)
db = client["hackathonDB"]
collection = db["events"]

# Function to parse MLH event dates
def parse_mlh_date(date_text):
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
    return None, None

# Chrome WebDriver Setup
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in background
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# MLH Hackathon Page
url = "https://mlh.io/seasons/2025/events"
driver.get(url)

hackathons_list = []
time.sleep(5)
WebDriverWait(driver, 15).until(
    EC.presence_of_all_elements_located((By.CLASS_NAME, "container"))
)

feature_containers = driver.find_elements(By.CLASS_NAME, "container")
for container in feature_containers:
    row = container.find_element(By.CLASS_NAME, "row")
    event_wrappers = row.find_elements(By.CLASS_NAME, "event-wrapper")

    if event_wrappers:
        for event in event_wrappers:
            name = event.find_element(By.CLASS_NAME, "event-name").text.strip()
            date_text = event.find_element(By.CLASS_NAME, "event-date").text.strip()
            location = event.find_element(By.CLASS_NAME, "event-location").text.strip()
            website = event.find_element(By.TAG_NAME, "a").get_attribute("href")

            try:
                mode = event.find_element(By.CLASS_NAME, "event-hybrid-notes").text.strip()
            except:
                mode = "Unknown"

            if mode == "Digital Only":
                mode, location = "Online", "Everywhere"
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
        break  # Stop searching after finding valid events

# Insert into MongoDB
if hackathons_list:
    collection.insert_many(hackathons_list)

driver.quit()
