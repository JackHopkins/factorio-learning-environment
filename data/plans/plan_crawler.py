import json
import http.client
import math
import os
import random
import time
from multiprocessing import Pool

import requests
import re
from bs4 import BeautifulSoup
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from typing import Dict, List, Optional, Tuple
import logging
import urllib.parse
from data.plans.prompts import classifier_prompt, extract_steps

load_dotenv()


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def split_queries(queries: List[str], num_splits: int) -> List[List[str]]:
    """Split queries into approximately equal chunks"""
    chunk_size = math.ceil(len(queries) / num_splits)
    return [queries[i : i + chunk_size] for i in range(0, len(queries), chunk_size)]


def crawler_worker(args: Tuple[List[str], str, str, int]):
    """Worker function for parallel processing"""
    queries, serper_key, openai_key, worker_id = args
    crawler = FactorioCrawler(
        serper_api_key=serper_key, openai_api_key=openai_key, worker_id=worker_id
    )
    crawler.process_all(queries)


class FactorioCrawler:
    def __init__(self, serper_api_key: str, openai_api_key: str, worker_id: int = 0):
        self.serper_api_key = serper_api_key
        self.client = OpenAI(api_key=openai_api_key)
        self.worker_id = worker_id
        self.base_dir = Path("factorio_guides")
        self.base_dir.mkdir(exist_ok=True)

        # Create visited URLs directory
        self.visited_dir = self.base_dir / "visited"
        self.visited_dir.mkdir(exist_ok=True)

        # Create a worker-specific lock file for URL visiting
        self.lock_file = self.visited_dir / f"worker_{worker_id}.lock"

    def url_to_filename(self, url: str) -> str:
        """Convert URL to a safe filename"""
        # Remove protocol and www
        clean_url = re.sub(r"^https?://(www\.)?", "", url)
        # Convert to safe filename using URL encoding
        return urllib.parse.quote_plus(clean_url)

    def is_url_visited(self, url: str) -> bool:
        """Check if URL has been visited before"""
        filename = self.url_to_filename(url)
        return (self.visited_dir / filename[:200]).exists()

    def mark_url_visited(self, url: str):
        """Mark URL as visited"""
        filename = self.url_to_filename(url)
        (self.visited_dir / filename[:200]).touch()

    def clean_content(self, text: str) -> str:
        """Clean and normalize text content"""
        # Replace multiple newlines with max two newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove excess whitespace
        text = re.sub(r"[ \t]+", " ", text)

        # Remove spaces at the beginning of lines
        text = re.sub(r"(?m)^[ \t]+", "", text)

        # Remove spaces at the end of lines
        text = re.sub(r"(?m)[ \t]+$", "", text)

        # Ensure consistent newline character
        text = text.replace("\r\n", "\n")

        # Remove any zero-width spaces or other invisible characters
        text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

        # Standardize unicode quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(""", "'").replace(""", "'")
        text = text.replace("—", "-").replace("–", "-")

        return text.strip()

    def search_guides(self, query: str) -> Dict:
        """Search for Factorio guides using SERPER API"""
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({"q": f"factorio {query} guide tutorial tips", "num": 100})
        headers = {"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"}

        try:
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))
            return data
        except Exception as e:
            logger.error(f"Error searching guides: {e}")
            return {}

    def fetch_page_content(self, url: str) -> str:
        """Fetch and parse webpage content"""
        try:
            response = requests.get(url, headers={"User-Agent": "FactorioCrawler/1.0"})
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            content = soup.get_text()
            return self.clean_content(content)
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return ""

    def save_raw_content(self, content: str, url: str):
        """Save raw content to filesystem"""
        file_path = self.base_dir / "raw" / f"{hash(url)}.txt"
        file_path.parent.mkdir(exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n\n")
            f.write(content)

    def classify_content(self, content: str) -> bool:
        """Use GPT-4 to classify if content contains instructions"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": classifier_prompt},
                    {
                        "role": "user",
                        "content": content[:8000],
                    },  # Truncate to avoid token limits
                ],
            )
            return response.choices[0].message.content.strip().lower() == "true"
        except Exception as e:
            logger.error(f"Error classifying content: {e}")
            return False

    def extract_steps(self, content: str) -> Optional[str]:
        """Extract steps from content using GPT-4"""
        string = ""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": extract_steps},
                    {"role": "user", "content": content[:4000]},
                ],
            )

            string = response.choices[0].message.content.strip()
            string = string.replace("```xml", "").replace("```", "")
            return string
        except Exception as e:
            logger.error(f"Error extracting steps: {e}\n\n{string}\n===")
            return None

    def save_guide(self, object: str, url: str):
        """Save processed XML guide"""
        file_path = self.base_dir / "processed" / f"{hash(url)}.xml"
        file_path.parent.mkdir(exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(object)

    def process_all(self, search_queries: List[str]):
        """Main processing function"""
        logger.info(
            f"Worker {self.worker_id} starting with {len(search_queries)} queries"
        )

        for query in search_queries:
            logger.info(f"Worker {self.worker_id} processing query: {query}")
            search_results = self.search_guides(query)

            if "organic" not in search_results:
                continue

            for result in search_results["organic"]:
                url = result.get("link")
                if not url:
                    continue

                if "youtube" in url.lower():
                    continue

                # Use file-based locking for URL visited check
                if self.is_url_visited(url):
                    logger.info(
                        f"Worker {self.worker_id} skipping previously visited URL: {url}"
                    )
                    continue

                # Respect rate limits - different delay for each worker
                time.sleep(1 + (self.worker_id * 0.1))  # Stagger requests

                # Fetch and save raw content
                content = self.fetch_page_content(url)
                if not content:
                    continue

                self.save_raw_content(content, url)

                # Classify content
                if not self.classify_content(content):
                    self.mark_url_visited(url)
                    continue

                # Extract and save steps
                root = self.extract_steps(content)
                if root is not None:
                    self.save_guide(root, url)

                # Mark URL as visited after processing
                self.mark_url_visited(url)


def main():
    SERPER_KEYS = os.getenv("SERPER_KEYS")
    SERPER_KEYS = SERPER_KEYS.split(",")
    # Configuration
    num_workers_per_key = 2
    total_workers = len(SERPER_KEYS) * num_workers_per_key
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Comprehensive early-game search queries
    search_queries = [
        # Absolute Basics
        "beginner guide first steps",
        "getting started tutorial",
        "first hour guide",
        "basic controls tutorial",
        "survival basics guide",
        "early game tips tricks",
        # Initial Resources
        "coal mining guide early",
        "iron mining setup",
        "copper mining basics",
        "stone mining early game",
        "manual resource gathering",
        "starting resource management",
        # First Automation
        "burner inserter setup",
        "first automation steps",
        "basic mining drill layout",
        "steam power setup",
        "coal power generation",
        "basic inserter patterns",
        "early smelting setup",
        # Science Production
        "red science automation",
        "green science setup",
        "early research guide",
        "science pack production",
        "research priorities guide",
        "laboratory setup guide",
        # Basic Infrastructure
        "belt layout guide",
        "early game logistics",
        "transport belt basics",
        "inserter mechanics guide",
        "chest usage tutorial",
        "underground belt guide",
        "splitter tutorial basic",
        # Power Systems
        "basic power setup",
        "steam engine layout",
        "boiler configuration",
        "power management early",
        "electricity network guide",
        "power pole placement",
        # Defense
        "early game defense",
        "basic military setup",
        "turret placement guide",
        "ammunition production",
        "wall construction guide",
        "biter defense basics",
        "early game military research",
        # Manufacturing
        "basic factory layout",
        "early production lines",
        "assembling machine setup",
        "manufacturing priorities",
        "component production guide",
        "intermediate products guide",
        # Resource Processing
        "basic ore processing",
        "early smelting layouts",
        "furnace setup guide",
        "plate production tutorial",
        "smelting column design",
        # Fluids
        "basic fluid handling",
        "pipe systems tutorial",
        "offshore pump setup",
        "early oil processing",
        "fluid storage basics",
        "pump mechanics guide",
        # Organization
        "main bus concept",
        "early base organization",
        "factory planning guide",
        "basic ratios tutorial",
        "production efficiency",
        "base layout principles",
        # Expansion
        "base expansion guide",
        "resource outpost setup",
        "early trains tutorial",
        "expanding production guide",
        "scaling up basics",
        # Specific Production Lines
        "electronic circuit production",
        "iron gear wheel automation",
        "copper cable manufacturing",
        "steel production setup",
        "basic materials flow",
        # Common Problems
        "bottleneck solutions early",
        "production backup fixes",
        "power shortage guide",
        "resource management tips",
        "common mistakes avoid",
        "troubleshooting guide early",
        # Efficiency
        "early game optimization",
        "basic factory ratios",
        "production efficiency guide",
        "resource balancing tips",
        "throughput optimization",
        # Quality of Life
        "early automation tips",
        "manual crafting guide",
        "inventory management",
        "quickbar setup guide",
        "hotkey optimization",
        # Progression Path
        "tech tree progression",
        "research order guide",
        "milestone planning",
        "advancement strategy",
        "progress benchmarks",
        # Starting Automation
        "first automation priority",
        "automating coal mining",
        "basic inserter chains",
        "burner phase automation",
        "crafting queue efficiency",
        "manual to automated transition",
        # Early Production
        "iron plate automation",
        "copper plate production line",
        "basic materials flow",
        "starter base layout",
        "initial factory setup",
        "early game ratios",
        # Resource Collection
        "automated mining setup",
        "coal power sustainability",
        "ore patch efficiency",
        "starting miners layout",
        "resource field optimization",
        "initial mining outpost",
        # Power Management
        "early power scaling",
        "coal supply automation",
        "power consumption planning",
        "backup power systems",
        "power grid layout",
        "electricity management tips",
        # Basic Logistics
        "initial belt systems",
        "early sorting methods",
        "basic item routing",
        "starter bus design",
        "item balancing early",
        "material distribution",
        # Science Production
        "automated red science",
        "science pack scaling",
        "research automation",
        "lab feeding setup",
        "science production ratio",
        "research facility layout",
        # Military Production
        "automated ammo production",
        "turret feeding systems",
        "military supply chain",
        "defensive production",
        "automated wall building",
        "military automation priority",
        # Component Production
        "gear wheel automation",
        "circuit production line",
        "inserter manufacturing",
        "belt production setup",
        "automated components",
        "intermediate products flow",
        # Early Base Design
        "starter factory layout",
        "production block design",
        "early game spacing",
        "factory organization",
        "modular design basics",
        "scalable layouts early",
        # Resource Management
        "coal distribution system",
        "ore processing layout",
        "plate balancing setup",
        "resource priority system",
        "material overflow handling",
        "resource buffer design",
        # Production Lines
        "assembly line basics",
        "production cell design",
        "manufacturing blocks",
        "automated crafting setup",
        "production flow design",
        "assembly machine layout",
        # Belt Systems
        "belt balancing early",
        "underground belt usage",
        "splitter arrangements",
        "belt compression tips",
        "belt priority system",
        "logistics optimization",
        # Power Grid
        "steam engine array",
        "boiler automation",
        "coal power layout",
        "power pole coverage",
        "early grid design",
        "power distribution",
        # Factory Planning
        "initial base planning",
        "expansion preparation",
        "growth bottlenecks",
        "factory scaling tips",
        "base organization",
        "design principles early",
        # Optimization
        "early efficiency tips",
        "production bottlenecks",
        "throughput optimization",
        "resource efficiency",
        "automation priorities",
        "system bottlenecks",
        # Troubleshooting
        "common automation issues",
        "production line fixes",
        "power system problems",
        "belt backup solutions",
        "inserter timing fixes",
        "resource starvation",
        # Quality Improvements
        "factory efficiency",
        "automation upgrades",
        "production speed tips",
        "system improvements",
        "optimization methods",
        "performance enhancement",
        # Progression
        "automation milestones",
        "production goals",
        "development stages",
        "expansion timing",
        "upgrade priorities",
        "advancement planning",
    ]

    # shuffle queries
    search_queries = random.sample(search_queries, len(search_queries))

    # Split queries for workers
    query_chunks = split_queries(search_queries, total_workers)

    # Prepare worker arguments
    worker_args = []
    for key_idx, serper_key in enumerate(SERPER_KEYS):
        for worker_num in range(num_workers_per_key):
            worker_id = (key_idx * num_workers_per_key) + worker_num
            if worker_id < len(query_chunks):  # Ensure we have queries for this worker
                worker_args.append(
                    (query_chunks[worker_id], serper_key, openai_api_key, worker_id)
                )

    # Start parallel processing
    with Pool(processes=total_workers) as pool:
        pool.map(crawler_worker, worker_args)


if __name__ == "__main__":
    main()
