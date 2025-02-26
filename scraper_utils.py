import os
import time
import re
import urllib.parse
from datetime import datetime
from pymongo import MongoClient
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv  # Needed for Devfolio scraper

# Load environment variables
load_dotenv()

# MongoDB Connection
def get_mongo_client():
    """Returns a MongoDB client connected to the hackathonDB."""
    username = urllib.parse.quote_plus(os.getenv("MONGO_USER", ""))
    password = urllib.parse.quote_plus(os.getenv("MONGO_PASS", ""))
    
    if not username or not password:
        print("⚠️ Warning: MongoDB credentials are missing!")

    client = MongoClient(
        f"mongodb+srv://{username}:{password}@hackathondb.hwg5w.mongodb.net/?retryWrites=true&w=majority&appName=hackathondb"
    )
    return client["hackathonDB"]

# WebDriver Setup
def get_driver(undetected=False):
    """
    Returns a Selenium WebDriver.
    If `undetected=True`, use undetected_chromedriver (MLH Scraper needs this).
    """
    if undetected:
        import undetected_chromedriver as uc
        return uc.Chrome()

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless")  # Run without opening browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options)
