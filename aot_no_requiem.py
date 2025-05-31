import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Base settings
base_url_template = "https://www.aotnorequiem.com/assets/images/chapters/{}/en/"
chapters = [137, 138, 139, 140]  # Chapters to process
max_pages = 100  # Maximum number of sequential pages per chapter
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
base_download_dir = "jpg_downloads"  # Base directory for downloads
use_selenium = False  # Set to True for dynamic content

def setup_selenium():
    """Set up Selenium WebDriver with headless Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def is_valid_jpg(url):
    """Check if a JPG file exists and is valid using a HEAD request."""
    try:
        response = requests.head(url, headers=headers, timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            if 'image/jpeg' in content_type:
                content_length = int(response.headers.get('content-length', 0))
                if content_length > 0:
                    return True
        return False
    except requests.RequestException as e:
        print(f"Error checking {url}: {e}")
        return False

def find_non_sequential_jpgs(url, use_selenium=False):
    """Scrape the webpage for non-sequential JPG files (e.g., 14+15.jpg)."""
    jpg_files = set()
    jpg_pattern = r'[\w\-+]+\.jpg$'  # Matches 1.jpg, 14+15.jpg, etc.
    
    try:
        if use_selenium:
            print("Using Selenium to scrape dynamic content...")
            driver = setup_selenium()
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()
        else:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and re.search(jpg_pattern, src, re.IGNORECASE):
                full_url = urljoin(url, src)
                jpg_files.add(full_url)
        
        for tag in soup.find_all():
            for attr in tag.attrs:
                value = tag.get(attr)
                if value and isinstance(value, str) and re.search(jpg_pattern, value, re.IGNORECASE):
                    full_url = urljoin(url, value)
                    jpg_files.add(full_url)
        
        return jpg_files
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return set()

def check_non_sequential_patterns(base_url):
    """Explicitly check for known non-sequential patterns like 14+15.jpg."""
    non_sequential_files = set()
    patterns = [f"{i}+{i+1}.jpg" for i in range(1, max_pages)]
    for pattern in patterns:
        file_url = urljoin(base_url, pattern)
        if is_valid_jpg(file_url):
            non_sequential_files.add(file_url)
            print(f"Found non-sequential file: {file_url}")
    return non_sequential_files

def detect_missing_sequential_files(jpg_files):
    """Detect missing sequential JPG files."""
    sequential_files = []
    non_sequential_files = []
    
    for jpg in jpg_files:
        filename = jpg.split('/')[-1]
        if re.match(r'^\d+\.jpg$', filename, re.IGNORECASE):
            sequential_files.append(int(filename.replace('.jpg', '')))
        else:
            non_sequential_files.append(filename)
    
    sequential_files.sort()
    
    missing_files = []
    if sequential_files:
        max_num = max(sequential_files)
        for i in range(1, max_num + 1):
            if i not in sequential_files:
                missing_files.append(f"{i}.jpg")
    
    return sequential_files, non_sequential_files, missing_files

def download_jpg_files(jpg_files, download_dir):
    """Download JPG files to a chapter-specific directory."""
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    for jpg_url in jpg_files:
        try:
            filename = jpg_url.split('/')[-1]
            file_path = os.path.join(download_dir, filename)
            response = requests.get(jpg_url, headers=headers, stream=True, timeout=10)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded: {file_path}")
        except requests.RequestException as e:
            print(f"Failed to download {jpg_url}: {e}")

def process_chapter(chapter):
    """Process a single chapter: find and download JPG files."""
    base_url = base_url_template.format(chapter)
    chapter_dir = os.path.join(base_download_dir, str(chapter))
    jpg_files = set()
    
    # Step 1: Sequential JPG files
    print(f"\nProcessing Chapter {chapter}...")
    print(f"Scanning for sequential JPG files in {base_url}...")
    for page in range(1, max_pages + 1):
        file_url = urljoin(base_url, f"{page}.jpg")
        print(f"Checking {file_url}...")
        if is_valid_jpg(file_url):
            jpg_files.add(file_url)
    
    # Step 2: Non-sequential patterns
    print(f"\nChecking for non-sequential patterns like X+Y.jpg in Chapter {chapter}...")
    jpg_files.update(check_non_sequential_patterns(base_url))
    
    # Step 3: Scrape for additional JPGs
    print(f"\nScraping for other non-sequential JPG files in {base_url}...")
    non_sequential_jpgs = find_non_sequential_jpgs(base_url, use_selenium=use_selenium)
    jpg_files.update(non_sequential_jpgs)
    
    # Step 4: Output results
    if jpg_files:
        print(f"\nFound the following JPG files for Chapter {chapter}:")
        for url in sorted(jpg_files):
            print(url)
        print(f"\nTotal JPG files found: {len(jpg_files)}")
        
        # Step 5: Analyze sequential and missing files
        sequential_files, non_sequential_files, missing_files = detect_missing_sequential_files(jpg_files)
        
        if sequential_files:
            print(f"\nSequential JPG files found in Chapter {chapter}:", [f"{num}.jpg" for num in sequential_files])
        if non_sequential_files:
            print(f"Non-sequential JPG files found in Chapter {chapter}:", non_sequential_files)
        if missing_files:
            print(f"Missing sequential JPG files in Chapter {chapter}:", missing_files)
        else:
            print(f"No missing sequential JPG files in Chapter {chapter}.")
        
        # Step 6: Download JPG files
        print(f"\nDownloading JPG files for Chapter {chapter} to {chapter_dir}...")
        download_jpg_files(jpg_files, chapter_dir)
    else:
        print(f"\nNo JPG files found for Chapter {chapter}. Try setting use_selenium=True.")

def main():
    for chapter in chapters:
        process_chapter(chapter)

if __name__ == "__main__":
    main()