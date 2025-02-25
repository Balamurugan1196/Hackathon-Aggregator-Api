import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Function to convert date format
def parse_mlh_date(date_text):
    try:
        current_year = datetime.today().year  # Get the current year

        # Remove ordinal suffixes (st, nd, rd, th)
        date_text = re.sub(r"(ST|ND|RD|TH)", "", date_text, flags=re.IGNORECASE)

        # Regex pattern to match formats like: "FEB 21 - 23", "APR 1 - MAR 4", "JAN 10 - FEB 2"
        date_pattern = r"([A-Za-z]+) (\d{1,2})\s*-\s*((?:[A-Za-z]+ )?\d{1,2})"

        match = re.match(date_pattern, date_text.strip())
        if match:
            start_month_name, start_day, end_part = match.groups()

            # Convert month name to month number
            start_month_number = datetime.strptime(start_month_name[:3], "%b").month

            # Parse the start date
            start_date = datetime(current_year, start_month_number, int(start_day)).strftime("%Y-%m-%d")

            # Process the end date
            end_match = re.match(r"([A-Za-z]+ )?(\d{1,2})", end_part.strip())
            if end_match:
                end_month_name, end_day = end_match.groups()
                if end_month_name:  # If end date has a month (e.g., "FEB 2")
                    end_month_number = datetime.strptime(end_month_name[:3], "%b").month
                else:  # If only a day is given (e.g., "23"), assume same month
                    end_month_number = start_month_number

                # Parse the end date
                end_date = datetime(current_year, end_month_number, int(end_day)).strftime("%Y-%m-%d")
            else:
                end_date = start_date  # If no end date, it's a one-day event

            return start_date, end_date
        else:
            raise ValueError("Date format not recognized.")

    except Exception as e:
        print(f"❌ Error parsing date: {date_text}, {e}")
        return None, None

# Initialize WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-gpu")  # Helps with headless mode sometimes
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Open MLH hackathon page
url = "https://mlh.io/seasons/2025/events"
driver.get(url)
print("opened the page")
hackathons_list = []

try:
    # Wait for the main feature container to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "container feature"))
    )

    # Find all container elements
    feature_containers = driver.find_elements(By.CLASS_NAME, "container feature")

    for container in feature_containers:
        try:
            row = container.find_element(By.CLASS_NAME, "row")
            event_wrappers = row.find_elements(By.CLASS_NAME, "event-wrapper")

            if event_wrappers:
                print(f"✅ Found {len(event_wrappers)} upcoming events.")

                # Extract data from each event
                for event in event_wrappers:
                    try:
                        name = event.find_element(By.CLASS_NAME, "event-name").text.strip()
                        date_text = event.find_element(By.CLASS_NAME, "event-date").text.strip()
                        location = event.find_element(By.CLASS_NAME, "event-location").text.strip()
                        website = event.find_element(By.TAG_NAME, "a").get_attribute("href")

                        # Some events might not have mode information
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

                        print(event_data)  # Print instead of storing
                        hackathons_list.append(event_data)
                    except Exception as e:
                        print(f"❌ Error extracting event data: {e}")

                break  # Stop searching after finding the first valid container with events

        except Exception as e:
            print("⚠️ Skipping container due to missing elements:", e)

finally:
    driver.quit()
