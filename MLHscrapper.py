import os
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Securely fetch MongoDB credentials from GitHub Secrets
username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))

# MongoDB Atlas Connection
MONGO_URI = f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb"
client = MongoClient(MONGO_URI)
db = client["hackathonDB"]
collection = db["mlh_hackathons"]

# Chrome options for headless execution
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

# Initialize ChromeDriver
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Open MLH hackathons page
    driver.get("https://mlh.io/seasons/2024/events")

    # Wait for event list to load (increase time if necessary)
    WebDriverWait(driver, 50).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'container') and contains(@class, 'feature')]"))
    )

    print("✅ Page loaded successfully!")

    # Scraping event details
    events = driver.find_elements(By.XPATH, "//div[contains(@class, 'event')]")

    new_hackathons = []
    for event in events:
        try:
            name = event.find_element(By.CLASS_NAME, "event-name").text
            date = event.find_element(By.CLASS_NAME, "event-date").text
            location = event.find_element(By.CLASS_NAME, "event-location").text
            link = event.find_element(By.TAG_NAME, "a").get_attribute("href")

            hackathon_data = {
                "name": name,
                "date": date,
                "location": location,
                "link": link
            }

            # Check if the event already exists in MongoDB
            existing = collection.find_one({"name": name, "date": date})
            if not existing:
                new_hackathons.append(hackathon_data)
                collection.insert_one(hackathon_data)
                print(f"✅ Added: {name}")
            else:
                print(f"🔁 Skipping duplicate: {name}")

        except Exception as e:
            print(f"⚠️ Skipping an event due to an error: {e}")

    print(f"✅ Successfully stored {len(new_hackathons)} new hackathons in MongoDB!")

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    driver.quit()
    print("🔄 Driver closed.")
