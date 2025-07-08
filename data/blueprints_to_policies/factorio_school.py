import base64
import zlib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import json
import time
import os
import re
import logging
from collections import deque

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class FactorioScraper:
    def __init__(
        self, base_url="https://www.factorio.school/", output_dir="blueprints"
    ):
        self.base_url = base_url
        self.output_dir = output_dir
        self.blueprint_pattern = re.compile(
            r"https:\/\/www\.factorio\.school\/api\/blueprintData\/[\d\w]+\/"
        )
        self.visited_urls = set()
        self.blueprint_urls = set()

        # Set up Chrome options
        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument("--headless")  # Run in headless mode
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")

        # Initialize the driver
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.implicitly_wait(10)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create separate directory for decoded blueprints
        self.decoded_dir = os.path.join(output_dir, "decoded")
        os.makedirs(self.decoded_dir, exist_ok=True)

    def decode_blueprint(self, encoded_data):
        """
        Decode a Factorio blueprint from Base64
        Returns both the encoded and decoded data
        """
        try:
            # Remove the "0" version prefix if present
            if encoded_data.startswith("0"):
                encoded_data = encoded_data[1:]

            # Decode Base64
            decoded_data = base64.b64decode(encoded_data)

            # Decompress if needed (Factorio uses zlib compression)
            try:
                decompressed_data = zlib.decompress(decoded_data)
                decoded_json = json.loads(decompressed_data)
            except zlib.error:
                # If decompression fails, try parsing directly (might not be compressed)
                decoded_json = json.loads(decoded_data)

            return {"encoded": encoded_data, "decoded": decoded_json}
        except Exception as e:
            logging.error(f"Error decoding blueprint: {str(e)}")
            return None

    def __del__(self):
        """Cleanup when the object is destroyed"""
        if hasattr(self, "driver"):
            self.driver.quit()

    def wait_for_page_load(self, timeout=10):
        """Wait for the page to load completely"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState")
                == "complete"
            )
        except TimeoutException:
            logging.warning("Page load timeout - continuing anyway")

    def download_blueprint(self, url):
        """Download blueprint data from API URL"""
        try:
            # Extract blueprint ID from URL
            blueprint_id = url.strip("/").split("/")[-1]
            raw_output_file = os.path.join(self.output_dir, f"{blueprint_id}_raw.json")
            decoded_output_file = os.path.join(
                self.decoded_dir, f"{blueprint_id}_decoded.json"
            )

            # Skip if already downloaded
            if os.path.exists(raw_output_file) and os.path.exists(decoded_output_file):
                logging.info(f"Blueprint {blueprint_id} already exists, skipping")
                return

            # Open a new tab for the API request
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])

            self.driver.get(url)

            # Wait for the response to load
            pre_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )

            # Parse the raw API response
            raw_data = pre_element.text

            # Extract and decode the blueprint string
            if "blueprintData" in url:
                decoded_data = self.decode_blueprint(raw_data)
                if decoded_data:
                    # Save the decoded blueprint
                    with open(decoded_output_file, "w", encoding="utf-8") as f:
                        json.dump(decoded_data["decoded"], f, indent=2)

                    logging.info(
                        f"Successfully downloaded and decoded blueprint {blueprint_id}"
                    )
                else:
                    logging.error(f"Failed to decode blueprint {blueprint_id}")
            else:
                logging.error(
                    f"No blueprint string found in response for {blueprint_id}"
                )

            # Close the tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        except Exception as e:
            logging.error(f"Error downloading blueprint from {url}: {str(e)}")
            # Make sure we're on the main tab
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

        # Polite delay between requests
        time.sleep(3)

    def find_blueprint_urls(self):
        """Find all blueprint API URLs in the page source"""
        return set(self.blueprint_pattern.findall(self.driver.page_source))

    def get_page_links(self):
        """Get all links on the current page"""
        links = set()
        try:
            elements = self.driver.find_elements(By.TAG_NAME, "a")
            for element in elements:
                href = element.get_attribute("href")
                if href and href.startswith(self.base_url):
                    links.add(href)
        except Exception as e:
            logging.error(f"Error getting page links: {str(e)}")
        return links

    def scrape_page(self, url):
        """Scrape a single page for blueprint URLs and links to other pages"""
        try:
            self.driver.get(url)
            self.wait_for_page_load()

            # Wait for dynamic content to load
            time.sleep(3)

            # Find blueprint URLs in the page content
            blueprint_urls = self.find_blueprint_urls()
            self.blueprint_urls.update(blueprint_urls)

            # Find all links to other pages
            next_urls = set()
            for next_url in self.get_page_links():
                if next_url not in self.visited_urls:
                    next_urls.add(next_url)

            return next_urls

        except Exception as e:
            logging.error(f"Error scraping page {url}: {str(e)}")
            return set()

    def run(self):
        """Run the scraper"""
        try:
            # Queue for BFS
            queue = deque([self.base_url])

            while queue:
                current_url = queue.popleft()

                if current_url in self.visited_urls:
                    continue

                logging.info(f"Scraping page: {current_url}")
                self.visited_urls.add(current_url)

                # Scrape the page and get next URLs
                next_urls = self.scrape_page(current_url)
                queue.extend(next_urls)

                # Download any blueprints found
                current_blueprints = self.find_blueprint_urls()
                for blueprint_url in current_blueprints:
                    self.download_blueprint(blueprint_url)

                # Polite delay between page requests
                time.sleep(2)

            logging.info(
                f"Scraping complete! Found {len(self.blueprint_urls)} blueprints"
            )

        finally:
            self.driver.quit()


if __name__ == "__main__":
    scraper = FactorioScraper()
    scraper.run()
