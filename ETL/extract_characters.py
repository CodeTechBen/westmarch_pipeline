# pyright: reportUnknownMemberType=false
# pyright: reportCallIssue=false
# pyright: reportUnknownVariableType=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportUnknownParameterType=false
# pyright: reportReturnType=false

'''Extracts data from DND Beyond scraped from westmarches and prepares it for transformation and loading into the database.'''

import re
from datetime import datetime, timezone

import logging
from setup import setup_logging
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

def get_characters_page(url: str) -> dict[str, list[dict[str, str]]]: # type: ignore
    BASE_URL = "https://www.westmarches.games"
    logging.info(f"Extracting characters from URL: {url}")

    driver = setup_selenium()
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser') 
    driver.quit()

    players: dict[str, dict[str, any]] = {} # type: ignore

    for a in soup.select('a.MuiCardActionArea-root[href]'):
        href = a.get('href', '')
        if '/characters/' not in href: # pyright: ignore[reportOperatorIssue]
            continue

        full_url = BASE_URL + href # type: ignore

        # Character name
        img = a.find('img', alt=True)
        if not img:
            continue
        character_name = img['alt'].strip() # type: ignore

        # Discord name
        player_span = a.select_one('span[aria-label]')

        discord_name = player_span.get("aria-label", "").strip() # type: ignore
        logging.info(f"Found Discord name for character '{character_name}': {discord_name}")

        player_span_text = a.select_one('span.MuiTypography-caption')
        player_name = player_span_text.text.strip() if player_span_text else discord_name # type: ignore

        if discord_name not in players:
            players[discord_name] = {
                "discord_name": discord_name,
                "player_name": player_name,
                "characters": []
            }

        players[discord_name]["characters"].append({ # type: ignore
            "character_name": character_name,
            "westmarch_url": full_url,
        })

        return {"players": list(players.values())} # type: ignore

def get_character_sheet_link(soup: BeautifulSoup) -> str: # type: ignore
     '''Extracts character link from the DND Beyond character page.'''
     with open('character_page.html', 'w') as f:
         f.write(str(soup))
     a = soup.find('a', href=True, class_='mui-1t71q0j')
     if a:
         href = a['href']
         logging.info(f"Found character sheet link: {href}")
         return href # type: ignore
     logging.warning(f"No character sheet link found.")
     return None  # type: ignore

def get_character_sessions(soup: BeautifulSoup) -> list[dict[str, any]]: # type: ignore
    '''Extract all sessions (adventures) for a character.'''
    
    sessions = []
    BASE_URL = "https://www.westmarches.games"

    for a in soup.select('a.mui-14u38ga'):
        href = a.get("href")
        if not href or "/adventures/" not in href:
            continue

        session_url = BASE_URL + href # type: ignore

        # Session name
        title = a.select_one("h6")
        session_name = title.text.strip() if title else None

        # Date
        time_tag = a.select_one("time")
        session_date = time_tag.get("datetime") if time_tag else None

        # DM info
        dm_span = a.select_one('span[aria-label]')
        dm_discord = dm_span.get("aria-label") if dm_span else None

        dm_name_tag = a.select_one('.mui-vxcmzt .MuiTypography-body2')
        dm_name = dm_name_tag.text.strip() if dm_name_tag else None

        sessions.append({ # pyright: ignore[reportUnknownMemberType]
            "session_name": session_name,
            "date": session_date,
            "dm": {
                "discord_name": dm_discord,
                "player_name": dm_name
            },
            "session_url": session_url
        })

    return sessions # type: ignore


def get_character_page(url: str) -> str: # type: ignore
    '''Extracts character link from the DND Beyond character page.'''

    driver = setup_selenium()
    logging.info(f"Extracting character links from URL: {url}")

    driver.get(url)
    driver.implicitly_wait(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    driver.quit()
    link = get_character_sheet_link(soup)
    sessions = get_character_sessions(soup)  
    
    if not link or not sessions:
        logging.warning(f"No character sheet link found for {url}")
        return {"character_sheet": link if link else None, "sessions": sessions if sessions else []} # type: ignore
    return {
        "character_sheet": link,
        "sessions": sessions
    } # type: ignore

def extract_stats(data: dict) -> dict[str, int]: # type: ignore
    stats = {stat["id"]: stat["value"] for stat in data["stats"]}  # type: ignore

    return {
        "strength": stats.get(1),  # type: ignore
        "dexterity": stats.get(2),  # type: ignore
        "constitution": stats.get(3),  # type: ignore
        "intelligence": stats.get(4),  # type: ignore
        "wisdom": stats.get(5),  # type: ignore
        "charisma": stats.get(6),  # type: ignore
        "hit_points": data.get("baseHitPoints", 0),  # type: ignore
        "armor_class": data.get("armorClass", 0),  # type: ignore
        "passive_perception": data.get("passivePerception", 0)  # type: ignore
    }  # type: ignore

def extract_classes(data: dict) -> tuple[list[dict], int]: # type: ignore
    classes = []
    total_level = 0

    for c in data.get("classes", []): # type: ignore
        level = c.get("level", 0) # type: ignore
        total_level += level # type: ignore

        subclass_definition = c.get("subclassDefinition", {}) # type: ignore
        if not subclass_definition:
            logging.info(f"No subclass found for class '{c['definition']['name']}' in character ID {data.get('id')}")
        subclass_name = subclass_definition.get("name") if subclass_definition else None # type: ignore
        class_description = c.get("definition", {}).get("description", "No description available.") # type: ignore
        subclass_definition = c.get("subclassDefinition", {})
        subclass_description = subclass_definition.get("description", "No description available.") if subclass_definition else "No description available."
        classes.append({ # type: ignore
            "class_name": c["definition"]["name"],
            "subclass_name": subclass_name,
            "level": level,
            "class_description": class_description,
            "subclass_description": subclass_description
        })

    return classes, total_level # type: ignore

def extract_spell_slots(data: dict[str, any]) -> dict[str, dict[str, int]]: # type: ignore
    slots = data.get("spellSlots", []) # type: ignore
    
    return {
        str(slot["level"]): { # type: ignore
            "available": slot["available"],
            "used": slot["used"]
        }
        for slot in slots # type: ignore
    }

def extract_equipment(data: dict[str, any]) -> list[dict[str, any]]: # type: ignore
    equipment = []

    for item in data.get("inventory", []): # type: ignore
        definition = item.get("definition", {}) # type: ignore

        equipment.append({ # type: ignore
            "item_name": definition.get("name"), # type: ignore
            "type": definition.get("filterType"), # type: ignore
            "rarity": definition.get("rarity"), # type: ignore
            "is_magical": definition.get("isMagic", False), # type: ignore
            "quantity": item.get("quantity", 1), # type: ignore
            "tags": definition.get("tags", []) # type: ignore
        })

    return equipment # type: ignore

def extract_spells(data: dict[str, any]) -> list[dict[str, any]]:
    spells = []
    spell_groups = data.get("spells", {})

    if not spell_groups:
        return spells

    for spell_group in spell_groups.values():
        if not spell_group:
            continue

        for spell in spell_group:
            if not spell:
                continue

            definition = spell.get("definition")
            if not definition:
                continue
            component_map = {
                1: "Verbal",
                2: "Somatic",
                3: "Material"}

            raw_components: list[str] = definition.get("components", [])
            components = [component_map.get(c, str(c)) for c in raw_components]

            spells.append({
                "spell_name": definition.get("name"),
                "description": definition.get("description", ""),
                "level": definition.get("level"),
                "school": definition.get("school"),
                "casting_time": definition.get("castingTimeDescription"),
                "range": definition.get("range"),
                "duration": definition.get("duration"),
                "damage": definition.get("modifiers")[0].get("die").get("dieString") if definition.get("modifiers") else None,
                "is_concentration": definition.get("concentration", "Unknown"),
                "is_ritual": definition.get("ritual", "Unknown"),
                "components": ",".join(components),
                "material_components": definition.get("componentsDescription"),
                "consumes_material": "Material" in components,
                "tags": definition.get("tags", [])
            })

    return spells

def extract_name(data: dict[str, any]) -> str:
    name = data.get("username")
    if not name:
        logging.warning(f"No player name found for character ID {data.get('id')}")
        return None
    logging.info(f"Extracted player name: {name}")
    return name

def extract_race(data: dict[str, any]) -> str:
    race = data.get("race", {})
    race_name = race.get("fullName") if race else None
    race_description = race.get("description") if race else None

    if not race:
        logging.warning(f"No race found for character ID {data.get('id')}")
        return None
    logging.info(f"Extracted race: {race}")

    return {
        "name": race_name,
        "description": race_description
    }

def get_dnd_beyond_info(url: str) -> dict[str, any]:
    try:
        logging.info(f"Extracting DND Beyond info from URL: {url}")
        match = re.search(r'/characters/(\d+)', url)
    except Exception as e:
        logging.error(f"Error extracting character ID from URL '{url}': {e}")
        return None
    if not match:
        return None

    character_id = match.group(1)

    response = requests.get(f'{ENV["DND_BEYOND_API"]}{character_id}')
    if response.status_code != 200:
        return None

    data = response.json().get("data", {})

    stats = extract_stats(data)
    logging.info(f"Extracted stats for character ID {character_id}: {stats}")
    classes, level = extract_classes(data)
    logging.info(f"Extracted classes for character ID {character_id}: {classes} with total level {level}")
    spell_slots = extract_spell_slots(data)
    logging.info(f"Extracted spell slots for character ID {character_id}: {spell_slots}")
    equipment = extract_equipment(data)
    logging.info(f"Extracted equipment for character ID {character_id}: {equipment}")
    spells = extract_spells(data)
    logging.info(f"Extracted spells for character ID {character_id}: {spells}")
    player_name = extract_name(data)
    logging.info(f"Extracted player name for character ID {character_id}: {player_name}")
    race = extract_race(data)
    logging.info(f"Extracted race for character ID {character_id}: {race}")

    return {
        "player_name": player_name,
        "dnd_beyond_id": character_id,
        "level": level,
        "stats": stats,
        "classes": classes,
        "spell_slots": spell_slots,
        "equipment": equipment,
        "spells": spells,
        "race": race,
        "gold": data.get("currencies", {}).get("gp", 0)
    }



def get_latest_past_session(sessions: list[dict[str, any]]) -> dict[str, any]:
    now = datetime.now(timezone.utc)

    valid_sessions = [
        s for s in sessions
        if s["date"] and datetime.fromisoformat(s["date"].replace("Z", "+00:00")) <= now
    ]

    if not valid_sessions:
        return None

    return max(valid_sessions, key=lambda s: s["date"])

def extract() -> dict[str, list[dict[str, any]]]: # type: ignore
    '''Main function to execute the extraction process.'''
    setup_logging()

    logging.info("Database connection established.")
    players = get_characters_page(url=ENV['WESTMARCH_URL'])
    
    players_out_dict = {}
    characters_out = []
    sessions_out = {}
    character_growth_out = []
    character_class_out = []
    inventory_out = []
    spellbook_out = []
    items_out_dict: dict[str, dict[str, any]] = {}
    spells_out_dict: dict[str, dict[str, any]] = {}
    class_out_dict: dict[str, dict[str, any]] = {}
    subclass_out_dict: dict[str, dict[str, any]] = {}

    for player in players['players']:
        player_key = player["discord_name"]

        if player_key not in players_out_dict:
            players_out_dict[player_key] = {
                "player_key": player_key,
                "discord_name": player["discord_name"],
                "player_name": player["player_name"],
                "dnd_beyond_name": None  # fill later
            }

        for character in player['characters']:
            character_key = character["westmarch_url"].split("/")[-1]


            character_page = get_character_page(character['westmarch_url'])
            character['character_sheet'] = character_page['character_sheet']
            character['sessions'] = character_page['sessions']


            dnd_info = get_dnd_beyond_info(character['character_sheet'])
            if dnd_info and not players_out_dict[player_key]["dnd_beyond_name"]:
                players_out_dict[player_key]["dnd_beyond_name"] = dnd_info.get("player_name")

            if not dnd_info:
                continue


            characters_out.append({ 
                "character_key": character_key,
                "character_name": character["character_name"],
                "character_page_url": character["westmarch_url"],
                "dnd_beyond_id": dnd_info["dnd_beyond_id"],
                "race": dnd_info["race"],
                "player_key": player_key
            })

            for cls in dnd_info["classes"]:
                if cls["class_name"] not in class_out_dict:
                    class_out_dict[cls["class_name"]] = {
                        "class_name": cls["class_name"],
                        "description": cls.get("class_description", "No description available.")
                    }
                if cls["subclass_name"] and cls["subclass_name"] not in subclass_out_dict:
                    subclass_out_dict[cls["subclass_name"]] = {
                        "subclass_name": cls["subclass_name"],
                        "description": cls.get("subclass_description", "No description available."),
                        "class_name": cls["class_name"]
                    }

                character_class_out.append({
                    "character_key": character_key,
                    "class_name": cls["class_name"],
                    "subclass_name": cls["subclass_name"],
                    "level": cls["level"]
                })


            latest_session = get_latest_past_session(character["sessions"])

            if latest_session:
                session_key = latest_session["session_url"].split("/")[-1]

                if session_key not in sessions_out:
                    sessions_out[session_key] = {
                        "session_key": session_key,
                        "session_name": latest_session["session_name"],
                        "date": latest_session["date"],
                        "dm_player_key": latest_session["dm"]["discord_name"]
                    }

                character_growth_out.append({
                    "character_key": character_key,
                    "session_key": session_key,
                    "level": dnd_info["level"],
                    **dnd_info["stats"],
                    "gold": dnd_info["gold"],
                    "spell_slots": dnd_info["spell_slots"]
                })

            for item in dnd_info["equipment"]:
                if item["item_name"] not in items_out_dict:
                    items_out_dict[item["item_name"]] = item

                inventory_out.append({
                    "character_key": character_key,
                    "item_name": item["item_name"],
                    "quantity": item["quantity"],
                    "tags": item["tags"]
                })

            for spell in dnd_info["spells"]:
                spell_name = spell["spell_name"]

                if spell_name not in spells_out_dict:
                    spells_out_dict[spell_name] = spell

                spellbook_out.append({
                    "character_key": character_key,
                    "spell_name": spell_name
                })

    return {
        "players": list(players_out_dict.values()),
        "characters": characters_out,
        "sessions": list(sessions_out.values()),
        "character_growth": character_growth_out,
        "character_class": character_class_out,
        "inventory": inventory_out,
        "spellbook": spellbook_out,
        "spells": list(spells_out_dict.values()),
        "items": list(items_out_dict.values()),
        "classes": list(class_out_dict.values()),
        "subclasses": list(subclass_out_dict.values())
    }

if __name__ == "__main__":
    extract()
