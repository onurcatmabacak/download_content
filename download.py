from selenium import webdriver
from bs4 import BeautifulSoup
import requests
import os
import time
import sys

# for i in range(1,140):
i = sys.argv[1]

# Set up Selenium (use Chrome, Firefox, etc.)
basedir = 'bolum-' + str(i)
driver = webdriver.Chrome()
driver.get("https://www.mangazure.com/2020/11/attack-on-titan-bolum-" + str(i) + ".html")

# Wait for images to load
time.sleep(30)

# Parse page source
soup = BeautifulSoup(driver.page_source, 'html.parser')
driver.quit()

# Extract and download images
img_tags = soup.find_all('img')
os.makedirs(basedir, exist_ok=True)

for i, img in enumerate(img_tags):
    img_url = img.get('src')
    if img_url and img_url.startswith('http'):
        img_data = requests.get(img_url).content
        with open(f'{basedir}/image_{i}.jpg', 'wb') as f:
            f.write(img_data)
        print(f"Downloaded image_{i}.jpg")
