import re
import time
import os
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient

# Function to convert date format to ISO format
def parse_mlh_date(date_text):
    try:
        current_year = datetime.today().year  # Get the current year

        # Remove ordinal suffixes (st, nd, rd, th)
        date_text = re.sub(r"(ST|ND|RD|TH)", "", date_text, flags=re.IGNORECASE)

        # Match dates in the format: "January 15 - January 17" or "March 5"
        date_pattern = r"([A-Za-z]+) (\d{1,2})\s*(-?\s*[A-Za-z]+ \d{1,2})?"

        match = re.match(date_pattern, date_text.strip())
        if match:
            start_month_name, start_day, end_part = match.groups()

            # Convert month name to month number
            start_month_number = datetime.strptime(start_month_name, "%B").month

            # Parse the start date
            start_date = datetime(current_year, start_month_number, int(start_day)).strftime("%Y-%m-%d")

            if end_part:  # If there is an end date
                end_match = re.match(r"([A-Za-z]+) (\d{1,2})", end_part.strip())
                if end_match:
                    end_month_name, end_day = end_match.groups()
                    end_month_number = datetime.strptime(end_month_name, "%B").month

                    # Parse the end date
                    end_date = datetime(current_year, end_month_number, int(end_day)).strftime("%Y-%m-%d")
                else:
                    end_date = start_date  # If no end month, assume it's the same as start date
            else:
                end_date = start_date  # If no end date, it's a one-day event

            return start_date, end_date
        else:
            raise ValueError("Date format not recognized.")

    except Exception as e:
        print(f"❌ Error parsing date: {date_text}, {e}")
        return None, None

# Initialize Selenium WebDriver (Headless Mode for GitHub Actions)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode (important for GitHub Actions)
options.add_argument("--no-sandbox")  # Bypass OS security restrictions
options.add_argument("--disable-dev-shm-usage")  # Avoid crashes due to limited memory
options.add_argument("--ignore-certificate-errors")  
options.add_argument("--disable-web-security")  

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Connect to MongoDB
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))
client = MongoClient(f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb")
db = client["hackathonDB"]
collection = db["events"]

# Open the MLH hackathon page
url = "https://mlh.io/seasons/2025/events"
driver.get(url)

try:
    # Wait until at least one "container feature" is found (Increased to 15s for reliability)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "container.feature"))
    )

    # Get all "container feature" elements
    containers = driver.find_elements(By.CLASS_NAME, "container.feature")

    first_valid_row = None

    # Loop through each container to find the one with a "row" containing events
    for container in containers:
        rows = container.find_elements(By.CLASS_NAME, "row")
        for row in rows:
            if row.find_elements(By.CLASS_NAME, "event-wrapper"):  # Check if row has events
                first_valid_row = row
                break
        if first_valid_row:
            break  # Stop once we find the correct row

    if not first_valid_row:
        print("⚠️ No upcoming hackathons found.")
    else:
        events = first_valid_row.find_elements(By.CLASS_NAME, "event-wrapper")
        hackathons = []

        for event in events:
            hackathon = {}

            try:
                hackathon["name"] = event.find_element(By.CSS_SELECTOR, "h3.event-name").text.strip()
            except:
                hackathon["name"] = "N/A"

            try:
                mode_text = event.find_element(By.CLASS_NAME, "event-hybrid-notes").find_element(By.TAG_NAME, "span").text.strip()
                if "In-Person Only" in mode_text:
                    hackathon["mode"] = "Offline"
                elif "Digital Only" in mode_text:
                    hackathon["mode"] = "Online"
                else:
                    hackathon["mode"] = "Hybrid"  # Handles mixed or unspecified modes
            except:
                hackathon["mode"] = "N/A"

            try:
                hackathon["location"] = event.find_element(By.CLASS_NAME, "event-location").text.strip()
                if hackathon["mode"] == "Online":
                    hackathon["location"] = "Everywhere"
            except:
                hackathon["location"] = "N/A"

            try:
                date_text = event.find_element(By.CLASS_NAME, "event-date").text.strip()
                hackathon["start_date"], hackathon["end_date"] = parse_mlh_date(date_text)  # Convert to ISO format
            except:
                hackathon["start_date"], hackathon["end_date"] = "N/A", "N/A"

            try:
                hackathon["apply_link"] = event.find_element(By.TAG_NAME, "a").get_attribute("href")
            except:
                hackathon["apply_link"] = "N/A"

            hackathon["source"] = "MLH"  # Source tag

            hackathons.append(hackathon)

            # Sleep between each event scraping to avoid hitting server too often
            time.sleep(1)

    if hackathons:
        try:
            inserted_count = 0
            for hackathon in hackathons:
                if not collection.find_one({"name": hackathon["name"]}):  # Check if already exists
                    collection.insert_one(hackathon)
                    inserted_count += 1
            print(f"✅ Successfully stored {inserted_count} new hackathons in MongoDB!")
        except Exception as e:
            print(f"❌ MongoDB Insert Error: {e}")

finally:
    client.close()  # Close the MongoDB connection
    driver.quit()
