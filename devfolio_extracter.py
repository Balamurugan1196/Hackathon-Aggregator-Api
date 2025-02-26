from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from datetime import datetime
import time
import os
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Connection
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))
client = MongoClient(f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb")
db = client["hackathonDB"]
collection = db["events"]

# Setup WebDriver with Headless Mode
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in background
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)
driver.get("https://devfolio.co/hackathons/open")

wait = WebDriverWait(driver, 10)  # Set explicit wait

# Function to Auto-Scroll & Load More Hackathons
def auto_scroll():
    last_height = driver.execute_script("return document.body.scrollHeight")
    previous_count = 0

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Wait for new content

        # Get number of hackathons loaded
        cards = driver.find_elements(By.XPATH, '//*[@id="__next"]/div[2]/div[2]/div/div/div')
        current_count = len(cards)

        if current_count == previous_count:  # Stop when no new items load
            break
        previous_count = current_count

    print(f"✅ Total Hackathons Loaded: {current_count}")

# Start Scrolling
auto_scroll()

# Extract Hackathon Details
hackathon_list = []
cards = driver.find_elements(By.XPATH, '//*[@id="__next"]/div[2]/div[2]/div/div/div')

for card in cards:
    try:
        name = card.find_element(By.XPATH, './/div/div/div[1]/div[1]/div/a/h3').text
        raw_start_date = card.find_element(By.XPATH, './/div/div/div[3]/div/div[3]/p').text
        apply_link = card.find_element(By.XPATH, './/div/div/div[1]/div[1]/div/a').get_attribute("href")
        mode = card.find_element(By.XPATH, './/div/div/div[3]/div/div[1]/p').text.strip()

        mode = "Offline" if mode.lower() == "offline" else "Online"

        # Parse Start Date
        try:
            date_str = raw_start_date.replace("STARTS ", "").strip()
            start_date = datetime.strptime(date_str, "%d/%m/%y").strftime("%Y-%m-%d")
        except:
            start_date = None  # Handle incorrect date formats

        # Default values
        end_date = None
        location = "Unknown"

        hackathon_data = {
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "mode": mode,
            "location": location,
            "apply_link": apply_link,
            "source": "Devfolio"
        }

        hackathon_list.append(hackathon_data)

    except Exception as e:
        print(f"⚠️ Error extracting details: {e}")

# Insert into MongoDB (Avoid Duplicates)
if hackathon_list:
    for hackathon in hackathon_list:
        if not collection.find_one({"name": hackathon["name"], "source": "Devfolio"}):
            collection.insert_one(hackathon)

    print(f"\n✅ Successfully stored {len(hackathon_list)} new hackathons in MongoDB!\n")
else:
    print("\n❌ No hackathons extracted. Check for issues.\n")

driver.quit()
