import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('linkedin_debug.log')
    ]
)
class LinkedInJobApplier:
    def __init__(self):
        self.driver = self._init_browser()
        
    def _init_browser(self):
        """Configure stealth Chrome browser"""
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        return webdriver.Chrome(options=options)
    
    def login(self):
        """Handle LinkedIn authentication with multiple fallback strategies"""
        self.driver.get("https://www.linkedin.com/login")
        
        try:
            # Wait for either email/password form or Google auth button
            WebDriverWait(self.driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "username")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-tracking-control-name='public_jobs_google-sign-in']"))
                )
            )
            
            # Attempt Google login if available
            if self._is_google_login_available():
                self._handle_google_login()
            else:
                self._handle_manual_login()
            
            # Verify successful login
            WebDriverWait(self.driver, 30).until(
                EC.url_contains("linkedin.com/feed")
            )
            logging.info("Login successful!")
            
        except TimeoutException:
            self._take_screenshot("login_failure")
            raise RuntimeError("Login process timed out")

    def _is_google_login_available(self):
        """Check for Google login button presence"""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, 
                "button[data-tracking-control-name='public_jobs_google-sign-in']"
            ).is_displayed()
        except NoSuchElementException:
            return False

    def _handle_google_login(self):
        """Manage Google authentication flow"""
        logging.info("Attempting Google login...")
        original_window = self.driver.current_window_handle
        
        # Click Google button and wait for new window
        self.driver.find_element(
            By.CSS_SELECTOR, 
            "button[data-tracking-control-name='public_jobs_google-sign-in']"
        ).click()
        
        WebDriverWait(self.driver, 10).until(EC.number_of_windows_to_be(2))
        
        # Switch to Google login window
        for window_handle in self.driver.window_handles:
            if window_handle != original_window:
                self.driver.switch_to.window(window_handle)
                break
                
        logging.info("Complete Google login in the popup window...")
        input("Press Enter when Google login is complete...")
        
        # Switch back and wait for LinkedIn feed
        self.driver.switch_to.window(original_window)

    def _handle_manual_login(self):
        logging.info("Please complete manual LinkedIn login...")
        input("Press Enter when logged in...")
    
    def apply_to_jobs(self):
        """Main workflow: navigate, extract job listings, and output as JSON"""
        keywords = [
   "Mechatronics Engineer",
  "Automation Engineer",
  "Embedded Software Engineer",
  "Control Systems",
  "Robotics Intern",
  "ADAS Testing",
  "Automotive Software",
  "Industrial Automation",
  "IoT Development",
  "Python Robotics",
  "automotive racing",
  "test engineer"
]
        all_jobs = []
        for keyword in keywords:
            try:
                self._navigate_to_jobs(keyword)
                # Use _process_job_listings to re-query the DOM and extract details for each job card
                jobs = self._process_job_listings()
                all_jobs.extend(jobs)
                logging.info("Extracted job listings:\n%s", all_jobs)
            except Exception as e:
                self._take_screenshot("application_failure")
                raise RuntimeError(f"Application process failed: {str(e)}")
        try:
            json_output = json.dumps(all_jobs, indent=2, ensure_ascii=False)
            with open("job_listings.json", "w", encoding="utf-8") as f:
                    f.write(json_output)
            logging.info("All jobs saved to file.")
        except Exception as e:
            logging.error(f"Error writing to JSON file: {e}")
                
        self.driver.quit()
    
    def _navigate_to_jobs(self, keyword="intern"):
        job_search_url = (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={keyword}"
            "&location=United%20States"
            "&geoId=103323778"
            "&f_TPR=r86400"  # Last 24 hours
        )
        logging.debug("Navigating to job search URL: %s", job_search_url)
        self.driver.get(job_search_url)
        # Wait for at least one stable job card to appear using a stable attribute selector
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-occludable-job-id]"))
        )
    
    def _process_job_listings(self):
        logging.debug("Processing job listings.")
        jobs = []
        # Ensure the job cards are loaded
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-occludable-job-id]"))
        )
        # Get initial list of job cards (will re-query during iteration to avoid stale elements)
        job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
        total_jobs = len(job_cards)
        logging.debug("Found %d job cards.", total_jobs)
        for idx in range(total_jobs):
            try:
                # Re-fetch job cards to ensure fresh references
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
                job_card = job_cards[idx]
                self.driver.execute_script("arguments[0].scrollIntoView(true);", job_card)
                time.sleep(0.5)
                job_card.click()
                logging.debug("Clicked job card #%d", idx + 1)
                time.sleep(1)  # Allow job details to load
                details = self._extract_job_details(job_card)
                if details:
                    jobs.append(details)
                    logging.info("Extracted details for job #%d: %s", idx + 1, details)
                else:
                    logging.warning("Failed to extract details for job #%d", idx + 1)
                time.sleep(1)
            except Exception as e:
                logging.error("Error processing job #%d: %s", idx + 1, e)
        return jobs
    
    def _extract_job_details(self, job_card):
        
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                details = {}
                details['job_id'] = job_card.get_attribute("data-occludable-job-id")
                title_element = job_card.find_element(By.CSS_SELECTOR, "a.job-card-container__link")
                details['title'] = title_element.text.strip()
                details['job_url'] = title_element.get_attribute("href")
                company_element = job_card.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle")
                details['company'] = company_element.text.strip()
                location_element = job_card.find_element(By.CSS_SELECTOR, "ul.job-card-container__metadata-wrapper li")
                details['location'] = location_element.text.strip()
                
                # Attempt to extract the job description from the details panel
                try:
                    description_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "job-details"))
                    )
                    details['description'] = description_element.text.strip()
                except Exception as desc_exc:
                    logging.warning("Job description not found: %s", desc_exc)
                    details['description'] = ""
                    
                return details
            
            except StaleElementReferenceException:
                attempts += 1
                logging.debug("Stale element encountered while extracting job details. Attempt %d of %d", attempts, max_attempts)
                time.sleep(0.5)
            except Exception as e:
                logging.error("Unexpected error extracting details: %s", e)
                return None
        logging.warning("Exceeded maximum attempts for extracting job details.")
        return None

    
    def _take_screenshot(self, name):
        try:
            if self.driver.session_id:
                screenshot_file = f"{name}_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_file)
                logging.debug("Screenshot saved: %s", screenshot_file)
        except Exception as e:
            logging.error("Failed to capture screenshot: %s", e)

if __name__ == "__main__":
    try:
        applier = LinkedInJobApplier()
        applier.login()
        applier.apply_to_jobs()
    except Exception as e:
        logging.error("Critical error: %s", e)
        if 'applier' in locals():
            applier._take_screenshot("final_error")