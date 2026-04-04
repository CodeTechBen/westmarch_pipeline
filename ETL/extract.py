'''Extracts data from DND Beyond scraped from westmarches and prepares it for transformation and loading into the database.'''
import re

import logging
from setup import setup_logging, get_db_connection
from os import environ as ENV
from dotenv import load_dotenv

from bs4 import BeautifulSoup
from selenium import webdriver
import requests


load_dotenv()

def setup_selenium() -> webdriver.Chrome:
    '''Configures Selenium WebDriver for web scraping.'''
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    return driver

def get_characters_page_url(url: str) -> dict[str, str]:
    '''Extracts character data from the specified URL.
    Returns a dictionary of character_name -> character link.'''

    driver = setup_selenium()
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    links: dict[str, str] = {}

    # Target only the character tiles
    for a in soup.select('a.MuiCardActionArea-root[href]'):
        href = a['href']

        if '/characters/' not in href:
            continue

        full_url = "https://www.westmarches.games" + href # type: ignore

        # Extract name from img alt
        img = a.find('img', alt=True)
        if img:
            name = img['alt'].strip() # type: ignore
        else:
            continue  # skip if no name found

        links[name] = full_url

    return links

def get_character_sheet_link(url: str) -> str: # type: ignore
    '''Extracts character link from the DND Beyond character page.'''

    driver = setup_selenium()
    logging.info(f"Extracting character links from URL: {url}")

    driver.get(url)
    driver.implicitly_wait(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    a = soup.find('a', href=True, class_='mui-1t71q0j')

    if a:
        href = a['href']
        logging.info(f"Found link: {href}")
        return href # type: ignore

    logging.warning(f"No character sheet link found for {url}")
    return None # type: ignore

def extract_character(url: str) -> dict[str, str]: # type: ignore
    '''Extracts character data from the specified URL.'''
    match = re.search(r'https://www.dndbeyond.com/characters/(\d+)', url)
    if not match:
        logging.warning(f"URL does not match expected D&D Beyond format: {url}")
        return None # type: ignore
    
    character_id = match.group(1)
    logging.info(f"Extracted character ID: {character_id}")

    response = requests.get(f'{ENV["DND_BEYOND_API"]}{character_id}')
    if response.status_code == 200:
        logging.info(f"Successfully retrieved character data for ID: {character_id}")
        return response.json()
    logging.warning(f"Failed to retrieve character data for ID: {character_id}")
    return None # type: ignore

def main():
    '''Main function to execute the extraction process.'''
    setup_logging()
    # conn = get_db_connection()
    logging.info("Database connection established.")

    characters = get_characters_page_url(url=ENV['WESTMARCH_URL'])

    logging.info(f"Extracted {len(characters)} character links from the page.")
    character_sheets = {}
    for name, link in characters.items():
        logging.info(f"Character Name: {name}, URL: {link}")
        character_sheets[name] = get_character_sheet_link(link)

    with open('character_sheets.txt', 'w') as f:
        for name, sheet_url in character_sheets.items(): # type: ignore
            f.write(f"{name}: {extract_character(sheet_url)}\n") # pyright: ignore[reportUnknownArgumentType]
            break
    
    

if __name__ == "__main__":
    main()