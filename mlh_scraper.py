from scraper_utils import get_driver, get_mongo_client, By, WebDriverWait, EC, datetime, re, Keys
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize MongoDB connection
db = get_mongo_client()
collection = db["hackathons"]

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

def run_mlh_scraper():
    driver = get_driver(undetected=True)
    try:
        url = "https://mlh.io/seasons/2025/events"
        driver.get(url)
        logging.info(f"\U0001F310 Opened MLH page: {url}")
        
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
                        except Exception:
                            logging.error(f"❌ Error extracting event data: {traceback.format_exc()}")
                    break
            except Exception:
                logging.warning(f"⚠️ Skipping container due to missing elements: {traceback.format_exc()}")
    
        if hackathons_list:
            for event in hackathons_list:
                if event["start_date"] and event["end_date"] and not collection.find_one({"name": event["name"], "start_date": event["start_date"]}):
                    collection.insert_one(event)
            logging.info(f"✅ Inserted {len(hackathons_list)} events into MongoDB.")
        else:
            logging.warning("⚠️ No new events found to insert.")
    
    except Exception:
        logging.error(f"❌ An error occurred: {traceback.format_exc()}")
    
    finally:
        driver.quit()
        logging.info("🚪 WebDriver closed.")
