# pyright: reportUnknownMemberType=false
# pyright: reportCallIssue=false
# pyright: reportUnknownVariableType=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportUnknownParameterType=false
# pyright: reportReturnType=false

"""Extracts data from Westmarches and optional D&D Beyond links for loading into the database."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from os import environ as ENV
from typing import Any, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from setup import setup_logging
from dndbeyond_utils import get_dnd_beyond_info

load_dotenv()


def setup_selenium() -> webdriver.Chrome:
    """Configure Selenium WebDriver for scraping."""
    options = webdriver.ChromeOptions()
    # Uncomment for non-debug / server use:
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def get_characters_page(url: str) -> dict[str, list[dict[str, str]]]:
    """Scrape the Westmarches characters index page."""
    base_url = "https://www.westmarches.games"
    logging.info(f"Extracting characters from URL: {url}")

    driver = setup_selenium()
    url_test = "https://www.westmarches.games/communities/tower-frontiers/characters/cmjm4ibsq00bx05if3gjwy1e8"
    url_test2= "https://www.westmarches.games/communities/tower-frontiers/characters/cmjm4w8cx00iq05if9ikxsgyd"
    try:
        driver.get(url_test)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        driver.quit()

    players: dict[str, dict[str, Any]] = {}

    for a in soup.select("a.MuiCardActionArea-root[href]"):
        href = a.get("href", "")
        if "/characters/" not in href:
            continue

        full_url = base_url + href

        img = a.find("img", alt=True)
        if not img:
            logging.info("No img!!")
            continue
        character_name = img["alt"].strip()
        logging.info(f"Character_name = {character_name}")

        player_span = a.select_one("span[aria-label]")
        discord_name = player_span.get("aria-label", "").strip() if player_span else ""
        if not discord_name:
            logging.warning(f"Skipping character '{character_name}' with no Discord name.")
            continue

        player_span_text = a.select_one("span.MuiTypography-caption")
        player_name = player_span_text.text.strip() if player_span_text else discord_name

        if discord_name not in players:
            players[discord_name] = {
                "discord_name": discord_name,
                "player_name": player_name,
                "characters": [],
            }

        players[discord_name]["characters"].append({
            "character_name": character_name,
            "westmarch_url": full_url,
        })

    return {"players": list(players.values())}


def get_character_sheet_link(soup: BeautifulSoup) -> Optional[str]:
    """Find a D&D Beyond character link on a Westmarches character page."""
    a = soup.find("a", href=lambda h: h and "/characters/" in h)
    if a:
        href = a["href"]
        logging.info(f"Found D&D Beyond character sheet link: {href}")
        return href

    logging.info("No D&D Beyond character sheet link found on page.")
    return None


def get_character_sessions(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract all sessions/adventures for a character."""
    sessions = []
    base_url = "https://www.westmarches.games"

    for a in soup.select("a.mui-14u38ga"):
        href = a.get("href")
        if not href or "/adventures/" not in href:
            continue

        session_url = base_url + href

        title = a.select_one("h6")
        session_name = title.text.strip() if title else None

        time_tag = a.select_one("time")
        session_date = time_tag.get("datetime") if time_tag else None

        dm_span = a.select_one("span[aria-label]")
        dm_discord = dm_span.get("aria-label") if dm_span else None

        dm_name_tag = a.select_one(".mui-vxcmzt .MuiTypography-body2")
        dm_name = dm_name_tag.text.strip() if dm_name_tag else None

        sessions.append({
            "session_name": session_name,
            "date": session_date,
            "dm": {
                "discord_name": dm_discord,
                "player_name": dm_name,
            },
            "session_url": session_url,
        })

    return sessions


def get_character_page(url: str) -> dict[str, Any]:
    """Extract a Westmarches character page, optionally finding a D&D Beyond sheet."""
    logging.info(f"Extracting character page from URL: {url}")
    driver = setup_selenium()

    try:
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            logging.warning(f"Timed out waiting for page body on {url}")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        link = get_character_sheet_link(soup)
        sessions = get_character_sessions(soup)

        return {
            "character_sheet": link,
            "sessions": sessions,
        }

    except WebDriverException as e:
        logging.error(f"Selenium error while scraping {url}: {e}")
        return {
            "character_sheet": None,
            "sessions": [],
        }
    except Exception as e:
        logging.error(f"Unexpected error while scraping {url}: {e}")
        return {
            "character_sheet": None,
            "sessions": [],
        }
    finally:
        driver.quit()


def get_latest_past_session(sessions: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Get the latest session whose datetime is in the past."""
    now = datetime.now(timezone.utc)

    valid_sessions = []
    for session in sessions:
        session_date = session.get("date")
        if not session_date:
            continue

        try:
            parsed = datetime.fromisoformat(session_date.replace("Z", "+00:00"))
        except ValueError:
            logging.warning(f"Skipping session with invalid datetime: {session_date}")
            continue

        if parsed <= now:
            valid_sessions.append(session)

    if not valid_sessions:
        return None

    return max(valid_sessions, key=lambda s: s["date"])


def extract() -> dict[str, list[dict[str, Any]]]:
    """Main extraction flow."""
    setup_logging()
    logging.info("Starting Westmarches extraction.")

    players = get_characters_page(url=ENV["WESTMARCH_URL"])

    players_out_dict: dict[str, dict[str, Any]] = {}
    characters_out: list[dict[str, Any]] = []
    sessions_out: dict[str, dict[str, Any]] = {}
    character_growth_out: list[dict[str, Any]] = []
    character_class_out: list[dict[str, Any]] = []
    inventory_out: list[dict[str, Any]] = []
    spellbook_out: list[dict[str, Any]] = []

    items_out_dict: dict[str, dict[str, Any]] = {}
    spells_out_dict: dict[str, dict[str, Any]] = {}
    class_out_dict: dict[str, dict[str, Any]] = {}
    subclass_out_dict: dict[str, dict[str, Any]] = {}

    for player in players["players"]:
        player_key = player["discord_name"]

        if player_key not in players_out_dict:
            players_out_dict[player_key] = {
                "player_key": player_key,
                "discord_name": player["discord_name"],
                "player_name": player["player_name"],
                "dnd_beyond_name": None,
            }

        for character in player["characters"]:
            character_key = character["westmarch_url"].split("/")[-1]

            character_page = get_character_page(character["westmarch_url"])
            character["character_sheet"] = character_page["character_sheet"]
            character["sessions"] = character_page["sessions"]

            dnd_info = None
            if character.get("character_sheet"):
                dnd_info = get_dnd_beyond_info(character["character_sheet"])

            if dnd_info and not players_out_dict[player_key]["dnd_beyond_name"]:
                players_out_dict[player_key]["dnd_beyond_name"] = dnd_info.get("player_name")

            # Always register the character, even with no D&D Beyond sheet
            characters_out.append({
                "character_key": character_key,
                "character_name": character["character_name"],
                "character_page_url": character["westmarch_url"],
                "dnd_beyond_id": dnd_info["dnd_beyond_id"] if dnd_info else None,
                "race": dnd_info["race"] if dnd_info else None,
                "player_key": player_key,
            })

            # No D&D Beyond data? Skip enrichment, but keep base character row.
            if not dnd_info:
                continue

            for cls in dnd_info["classes"]:
                if cls["class_name"] not in class_out_dict:
                    class_out_dict[cls["class_name"]] = {
                        "class_name": cls["class_name"],
                        "description": cls.get("class_description", "No description available."),
                    }

                if cls["subclass_name"] and cls["subclass_name"] not in subclass_out_dict:
                    subclass_out_dict[cls["subclass_name"]] = {
                        "subclass_name": cls["subclass_name"],
                        "description": cls.get("subclass_description", "No description available."),
                        "class_name": cls["class_name"],
                    }

                character_class_out.append({
                    "character_key": character_key,
                    "class_name": cls["class_name"],
                    "subclass_name": cls["subclass_name"],
                    "level": cls["level"],
                })

            latest_session = get_latest_past_session(character["sessions"])

            if latest_session:
                session_key = latest_session["session_url"].split("/")[-1]

                if session_key not in sessions_out:
                    sessions_out[session_key] = {
                        "session_key": session_key,
                        "session_name": latest_session["session_name"],
                        "date": latest_session["date"],
                        "dm_player_key": latest_session["dm"]["discord_name"],
                    }

                character_growth_out.append({
                    "character_key": character_key,
                    "session_key": session_key,
                    "level": dnd_info["level"],
                    **dnd_info["stats"],
                    "gold": dnd_info["gold"],
                    "spell_slots": dnd_info["spell_slots"],
                })

            for item in dnd_info["equipment"]:
                if item["item_name"] not in items_out_dict:
                    items_out_dict[item["item_name"]] = item

                inventory_out.append({
                    "character_key": character_key,
                    "item_name": item["item_name"],
                    "quantity": item["quantity"],
                    "tags": item["tags"],
                })

            for spell in dnd_info["spells"]:
                spell_name = spell["spell_name"]

                if spell_name not in spells_out_dict:
                    spells_out_dict[spell_name] = spell

                spellbook_out.append({
                    "character_key": character_key,
                    "spell_name": spell_name,
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
        "subclasses": list(subclass_out_dict.values()),
    }


if __name__ == "__main__":
    data = extract()

    with open("character_extract.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)