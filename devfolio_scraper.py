from scraper_utils import get_driver, get_mongo_client, By, WebDriverWait, datetime
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize MongoDB connection
db = get_mongo_client()
collection = db["hackathons"]

# Initialize Selenium WebDriver
driver = get_driver()
if not driver:
    logging.error("❌ WebDriver initialization failed. Exiting script.")
    exit(1)

driver.get("https://devfolio.co/hackathons/open")
wait = WebDriverWait(driver, 10)

# Function to Auto-Scroll & Load More Hackathons
def auto_scroll():
    last_height = driver.execute_script("return document.body.scrollHeight")
    previous_count = 0
    max_attempts = 10  # Limit retries to prevent infinite loops

    while max_attempts > 0:
        driver.execute_script("window.scrollBy(0, window.innerHeight);")  # Scroll down a bit
        time.sleep(3)  # Wait for new content to load
        
        cards = driver.find_elements(By.XPATH, '//*[@id="__next"]/div[2]/div[2]/div/div/div')
        current_count = len(cards)

        if current_count == previous_count:  # Stop if no new items are loaded
            max_attempts -= 1  # Reduce attempts and try again
        else:
            max_attempts = 10  # Reset attempts if new items load

        previous_count = current_count

    logging.info(f"✅ Total Hackathons Loaded: {current_count}")

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
        logging.warning(f"⚠️ Error extracting details for a hackathon: {e}")

# Insert into MongoDB (Avoid Duplicates)
if hackathon_list:
    collection.insert_many(hackathon_list)  # Use the correct list name
    logging.info(f"✅ Successfully stored {len(hackathon_list)} new hackathons in MongoDB!")
else:
    logging.error("❌ No hackathons extracted. Check for issues.")

driver.quit()