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
import re
from datetime import datetime, timezone
from os import environ as ENV
from typing import Any, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from setup import setup_logging
from dndbeyond_utils import get_dnd_beyond_info

load_dotenv()

BASE_URL = "https://www.westmarches.games"


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def setup_selenium() -> webdriver.Chrome:
    options = Options()

    # Point Selenium to the browser binary inside the image
    options.binary_location = "/opt/chrome/chrome"

    # Lambda-safe flags
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--single-process")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")

    # Force Chrome to use Lambda's writable temp space
    options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    options.add_argument("--data-path=/tmp/chrome-data")
    options.add_argument("--disk-cache-dir=/tmp/chrome-cache")

    # Point Selenium to the chromedriver binary inside the image
    service = Service("/opt/chromedriver")

    return webdriver.Chrome(service=service, options=options)


def clean_text(value: Optional[str]) -> Optional[str]:
    """Normalize text."""
    if not value:
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def get_page_soup(
    driver: webdriver.Chrome,
    url: str,
    wait_seconds: int = 15,
) -> BeautifulSoup:
    """Load a page and return BeautifulSoup."""
    driver.get(url)
    WebDriverWait(driver, wait_seconds).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    return BeautifulSoup(driver.page_source, "html.parser")


def get_characters_page(url: str) -> dict[str, list[dict[str, str]]]:
    """Scrape the Westmarches characters index page."""
    logging.info(f"Extracting characters from URL: {url}")

    driver = setup_selenium()
    try:
        soup = get_page_soup(driver, url)
    finally:
        driver.quit()

    players: dict[str, dict[str, Any]] = {}

    for a in soup.select("a.MuiCardActionArea-root[href]"):
        href = a.get("href", "")
        if "/characters/" not in href:
            continue

        full_url = BASE_URL + href

        character_name = ""

        avatar_img = a.select_one(".avatar-image img")
        if avatar_img:
            character_name = avatar_img.get("alt", "").strip()

        if not character_name:
            avatar_div = a.select_one(".avatar-image[title]")
            if avatar_div:
                character_name = avatar_div.get("title", "").strip()

        if not character_name:
            for img in a.select("img[alt]"):
                alt_text = img.get("alt", "").strip()
                if alt_text:
                    character_name = alt_text
                    logging.debug(
                        f"Fallback alt_text used for character name: '{character_name}'"
                    )
                    break

        if not character_name:
            logging.warning(f"Skipping character card with no character name: {full_url}")
            continue

        player_span = a.select_one("span[aria-label]")
        discord_name = player_span.get("aria-label", "").strip() if player_span else ""
        if not discord_name:
            logging.warning(f"Skipping character '{character_name}' with no Discord name.")
            continue

        player_span_text = a.select_one("span.MuiTypography-caption")
        player_name = (
            player_span_text.get_text(strip=True) if player_span_text else discord_name
        )

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
    a = soup.find("a", href=lambda h: h and "dndbeyond.com/characters/" in h)
    if a:
        href = a["href"]
        logging.info(f"Found D&D Beyond character sheet link: {href}")
        return href

    a = soup.find("a", href=lambda h: h and "/characters/" in h)
    if a:
        href = a["href"]
        if "dndbeyond.com" in href:
            logging.info(f"Found D&D Beyond character sheet link: {href}")
            return href

    logging.info("No D&D Beyond character sheet link found on page.")
    return None


def get_character_page(url: str) -> dict[str, Any]:
    """Extract a Westmarches character page, optionally finding a D&D Beyond sheet."""
    logging.info(f"Extracting character page from URL: {url}")
    driver = setup_selenium()

    try:
        soup = get_page_soup(driver, url)
        link = get_character_sheet_link(soup)

        return {
            "character_sheet": link,
        }

    except TimeoutException:
        logging.warning(f"Timed out waiting for page body on {url}")
        return {"character_sheet": None}
    except WebDriverException as e:
        logging.error(f"Selenium error while scraping {url}: {e}")
        return {"character_sheet": None}
    except Exception as e:
        logging.error(f"Unexpected error while scraping {url}: {e}")
        return {"character_sheet": None}
    finally:
        driver.quit()


def extract_title_from_meta(soup: BeautifulSoup) -> Optional[str]:
    """Get the real adventure title from metadata."""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = clean_text(og_title["content"])
        if title:
            title = re.sub(
                r"\s*-\s*Tower Frontiers\s*-\s*WestMarches\.games\s*$",
                "",
                title,
            )
            return title

    twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    if twitter_title and twitter_title.get("content"):
        title = clean_text(twitter_title["content"])
        if title:
            title = re.sub(r"\s*-\s*Tower Frontiers\s*$", "", title)
            return title

    return None


def extract_gm_from_visible_html(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Extract DM from visible GM block."""
    gm_link = None

    for a in soup.select('a[href*="/gm/"]'):
        text = clean_text(a.get_text(" ", strip=True))
        if text and "Game Master" in text:
            gm_link = a
            break

    if not gm_link:
        return None, None

    player_name = None
    name_tag = gm_link.select_one("p")
    if name_tag:
        player_name = clean_text(name_tag.get_text(" ", strip=True))

    if not player_name:
        img = gm_link.select_one("img[alt]")
        if img:
            player_name = clean_text(img.get("alt"))

    discord_name = player_name
    return discord_name, player_name


def extract_gm_from_scripts(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Fallback DM extraction from embedded data."""
    html = str(soup)

    gm_match = re.search(
        r'"gm":\{.*?"nicknames":\{.*?"nickname":"([^"]+)".*?"displayName":"([^"]+)"',
        html,
        re.DOTALL,
    )
    if gm_match:
        nickname = clean_text(gm_match.group(1))
        display_name = clean_text(gm_match.group(2))
        return nickname, nickname or display_name

    gm_match = re.search(
        r'"gmInfo":\{.*?"user":\{.*?"nicknames":\{.*?"nickname":"([^"]+)".*?"displayName":"([^"]+)"',
        html,
        re.DOTALL,
    )
    if gm_match:
        nickname = clean_text(gm_match.group(1))
        display_name = clean_text(gm_match.group(2))
        return nickname, nickname or display_name

    return None, None


def extract_players_from_visible_html(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Extract players from visible participant cards."""
    players: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for block in soup.select("div.MuiPaper-root"):
        text = " ".join(block.stripped_strings)

        if "APPROVED" not in text:
            continue

        char_link = block.select_one('a[href*="/characters/"]')
        if not char_link:
            continue

        title_link = block.select_one(
            'a.MuiTypography-root.MuiTypography-h6[href*="/characters/"]'
        )
        if not title_link:
            continue

        character_name = clean_text(title_link.get_text(" ", strip=True))
        character_href = char_link.get("href", "").strip()
        character_url = (
            BASE_URL + character_href if character_href.startswith("/") else character_href
        )

        owner = block.select_one('[aria-label^="@"]')
        player_name = None

        if owner:
            visible_owner = owner.select_one(".MuiTypography-body2")
            if visible_owner:
                player_name = clean_text(visible_owner.get_text(" ", strip=True))

            if not player_name:
                owner_text = clean_text(owner.get_text(" ", strip=True))
                if owner_text:
                    player_name = owner_text

            if not player_name:
                aria = clean_text(owner.get("aria-label"))
                if aria:
                    player_name = aria.removeprefix("@")

        if not character_name or not player_name or not character_url:
            continue

        key = (player_name, character_name, character_url)
        if key in seen:
            continue

        seen.add(key)
        players.append({
            "player_name": player_name,
            "character_name": character_name,
            "character_url": character_url,
        })

    return players


def get_adventure_links(soup: BeautifulSoup) -> list[str]:
    """Extract unique adventure URLs from the community adventures page."""
    links: list[str] = []
    seen: set[str] = set()

    for a in soup.select('a[href*="/adventures/"]'):
        href = a.get("href", "").strip()
        if not href:
            continue
        if "/communities/" not in href or "/adventures/" not in href:
            continue

        full_url = BASE_URL + href if href.startswith("/") else href
        if full_url in seen:
            continue

        seen.add(full_url)
        links.append(full_url)

    return links


def get_adventure_detail(driver: webdriver.Chrome, url: str) -> Optional[dict[str, Any]]:
    """Extract one adventure detail page."""
    logging.info(f"Extracting adventure page: {url}")

    try:
        soup = get_page_soup(driver, url)
    except Exception as e:
        logging.error(f"Failed to load adventure page {url}: {e}")
        return None

    session_name = extract_title_from_meta(soup)
    if not session_name:
        title_tag = soup.select_one("h1")
        if title_tag:
            session_name = clean_text(title_tag.get_text(" ", strip=True))

    time_tag = soup.select_one("time[datetime]")
    session_date = time_tag.get("datetime") if time_tag else None

    dm_discord, dm_name = extract_gm_from_visible_html(soup)
    if not dm_discord and not dm_name:
        dm_discord, dm_name = extract_gm_from_scripts(soup)

    participants = extract_players_from_visible_html(soup)

    session_key = url.rstrip("/").split("/")[-1]

    return {
        "session_key": session_key,
        "session_name": session_name,
        "date": session_date,
        "dm": {
            "discord_name": dm_discord,
            "player_name": dm_name,
        },
        "players": participants,
        "session_url": url,
    }


def get_all_adventures(adventures_url: str) -> list[dict[str, Any]]:
    """Scrape the community adventures page and all linked adventure detail pages."""
    logging.info(f"Extracting adventures from listing page: {adventures_url}")
    driver = setup_selenium()

    try:
        listing_soup = get_page_soup(driver, adventures_url)
        adventure_links = get_adventure_links(listing_soup)
        logging.info(f"Found {len(adventure_links)} adventure links")

        adventures: list[dict[str, Any]] = []
        for url in adventure_links:
            adventure = get_adventure_detail(driver, url)
            if adventure:
                adventures.append(adventure)

        return adventures

    except TimeoutException:
        logging.warning(f"Timed out waiting for adventures page body on {adventures_url}")
        return []
    except WebDriverException as e:
        logging.error(f"Selenium error while scraping adventures page {adventures_url}: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error while scraping adventures page {adventures_url}: {e}")
        return []
    finally:
        driver.quit()


def split_sessions_by_time(
    sessions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split sessions into past and upcoming."""
    now = datetime.now(timezone.utc)
    past_sessions: list[dict[str, Any]] = []
    upcoming_sessions: list[dict[str, Any]] = []

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
            past_sessions.append(session)
        else:
            upcoming_sessions.append(session)

    return past_sessions, upcoming_sessions


def get_latest_past_session(sessions: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Get the latest session whose datetime is in the past."""
    past_sessions, _ = split_sessions_by_time(sessions)
    if not past_sessions:
        return None
    return max(past_sessions, key=lambda s: s["date"])


def build_character_session_map(
    players: dict[str, list[dict[str, Any]]],
    adventures: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Map adventures back to characters using exact character URLs."""
    known_character_urls: dict[str, str] = {}

    for player in players["players"]:
        for character in player["characters"]:
            character_key = character["westmarch_url"].split("/")[-1]
            known_character_urls[character["westmarch_url"]] = character_key

    character_sessions: dict[str, list[dict[str, Any]]] = {}

    for adventure in adventures:
        session_stub = {
            "session_key": adventure["session_key"],
            "session_name": adventure["session_name"],
            "date": adventure["date"],
            "dm": adventure["dm"],
            "players": adventure["players"],
            "session_url": adventure["session_url"],
        }

        for participant in adventure["players"]:
            participant_url = participant.get("character_url")
            if not participant_url:
                continue

            character_key = known_character_urls.get(participant_url)
            if not character_key:
                continue

            character_sessions.setdefault(character_key, []).append(session_stub)

    for character_key, sessions in character_sessions.items():
        deduped: dict[str, dict[str, Any]] = {}
        for session in sessions:
            deduped[session["session_key"]] = session

        character_sessions[character_key] = sorted(
            deduped.values(),
            key=lambda s: s.get("date") or "",
        )

    return character_sessions


def extract() -> dict[str, list[dict[str, Any]]]:
    """Main extraction flow."""
    setup_logging()
    logging.info("Starting Westmarches extraction.")

    players = get_characters_page(url=ENV["WESTMARCH_URL"])

    adventures_url = ENV.get(
        "WESTMARCH_ADVENTURES_URL",
        "https://www.westmarches.games/communities/tower-frontiers/adventures",
    )
    adventures = get_all_adventures(adventures_url)
    character_session_map = build_character_session_map(players, adventures)

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
            character["sessions"] = character_session_map.get(character_key, [])

            dnd_info = None
            if character.get("character_sheet"):
                dnd_info = get_dnd_beyond_info(character["character_sheet"])

            if dnd_info and not players_out_dict[player_key]["dnd_beyond_name"]:
                players_out_dict[player_key]["dnd_beyond_name"] = dnd_info.get("player_name")

            characters_out.append({
                "character_key": character_key,
                "character_name": character["character_name"],
                "character_page_url": character["westmarch_url"],
                "dnd_beyond_id": dnd_info["dnd_beyond_id"] if dnd_info else None,
                "race": dnd_info["race"] if dnd_info else None,
                "player_key": player_key,
            })

            # Register all linked sessions for output
            for session in character["sessions"]:
                session_key = session["session_key"]

                if session_key not in sessions_out:
                    sessions_out[session_key] = {
                        "session_key": session_key,
                        "session_name": session["session_name"],
                        "date": session["date"],
                        "dm_player_key": session["dm"]["discord_name"],
                        "dm_player_name": session["dm"]["player_name"],
                        "players": [
                            {
                                "player_name": p["player_name"],
                                "character_name": p["character_name"],
                            }
                            for p in session["players"]
                        ],
                    }

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
                session_key = latest_session["session_key"]

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