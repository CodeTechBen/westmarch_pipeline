from __future__ import annotations

import json
import re
from typing import Any, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "https://www.westmarches.games"
ADVENTURES_URL = "https://www.westmarches.games/communities/tower-frontiers/adventures"


def setup_selenium() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def get_page_soup(
    driver: webdriver.Chrome,
    url: str,
    output_file: Optional[str] = None
) -> BeautifulSoup:
    driver.get(url)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    html = driver.page_source
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

    return BeautifulSoup(html, "html.parser")


def clean_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def get_adventure_links(soup: BeautifulSoup) -> list[str]:
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

def debug_first_participant_blocks(soup: BeautifulSoup) -> None:
    print("\n=== DEBUG: visible participant blocks ===")

    blocks = soup.select("div.MuiPaper-root")
    print(f"Total MuiPaper blocks: {len(blocks)}")

    found = 0

    for idx, block in enumerate(blocks):
        text = " ".join(block.stripped_strings)

        # Only inspect blocks that look like participant cards
        if "APPROVED" not in text:
            continue
        if "/characters/" not in str(block):
            continue

        found += 1
        print(f"\n--- Participant block #{found} (paper index {idx}) ---")
        print(text[:800])

        char_link = block.select_one('a[href*="/characters/"]')
        if char_link:
            print("char_link href:", char_link.get("href"))

        title_link = block.select_one('a.MuiTypography-root.MuiTypography-h6[href*="/characters/"]')
        print("title_link found:", bool(title_link))
        if title_link:
            print("title_link text:", title_link.get_text(" ", strip=True))

        aria_owner = block.select_one('[aria-label^="@"]')
        print("aria owner found:", bool(aria_owner))
        if aria_owner:
            print("aria-label:", aria_owner.get("aria-label"))

        owner_img = block.select_one('[aria-label^="@"] img[alt]')
        print("owner img found:", bool(owner_img))
        if owner_img:
            print("owner img alt:", owner_img.get("alt"))

        char_img = block.select_one('.avatar-image img[alt]')
        print("character img found:", bool(char_img))
        if char_img:
            print("character img alt:", char_img.get("alt"))

        if found >= 3:
            break

    print(f"\nVisible participant-like blocks found: {found}")


def debug_participant_regex(soup: BeautifulSoup) -> None:
    print("\n=== DEBUG: regex participant matches ===")

    html = str(soup)

    participant_pattern = re.compile(
        r'"character":\{.*?"name":"([^"]+)".*?"user":\{.*?"name":"([^"]+)"',
        re.DOTALL,
    )

    matches = list(participant_pattern.finditer(html))
    print("regex match count:", len(matches))

    for i, match in enumerate(matches[:10], start=1):
        print(f"{i}. character={match.group(1)!r}, player={match.group(2)!r}")


def extract_title_from_meta(soup: BeautifulSoup) -> Optional[str]:
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
    """
    Best source: the visible GM card on the adventure detail page.
    """
    gm_link = None

    for a in soup.select('a[href*="/gm/"]'):
        text = clean_text(a.get_text(" ", strip=True))
        if text and "Game Master" in text:
            gm_link = a
            break

    if not gm_link:
        return None, None

    # Prefer visible GM name
    player_name = None
    name_tag = gm_link.select_one("p")
    if name_tag:
        player_name = clean_text(name_tag.get_text(" ", strip=True))

    # Fallback to avatar alt
    if not player_name:
        img = gm_link.select_one("img[alt]")
        if img:
            player_name = clean_text(img.get("alt"))

    # Discord name often isn't exposed visibly here, so fallback to same value
    discord_name = player_name

    return discord_name, player_name


def extract_gm_from_scripts(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """
    Fallback: extract GM info from embedded page data.
    On this page, nickname = 'Graham (Forever DM)' and displayName = 'Kisho'.
    We want the nickname for the visible campaign-facing name.
    """
    html = str(soup)

    # Prefer nickname, because that's what the page displays for the GM
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
    """
    Extract players from the visible participant cards.
    """
    players: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for block in soup.select("div.MuiPaper-root"):
        text = " ".join(block.stripped_strings)

        # Participant cards include APPROVED and a character link
        if "APPROVED" not in text:
            continue
        if not block.select_one('a[href*="/characters/"]'):
            continue

        title_link = block.select_one(
            'a.MuiTypography-root.MuiTypography-h6[href*="/characters/"]'
        )
        if not title_link:
            continue

        character_name = clean_text(title_link.get_text(" ", strip=True))

        owner = block.select_one('[aria-label^="@"]')
        player_name = None

        if owner:
            aria = clean_text(owner.get("aria-label"))
            if aria:
                player_name = aria.removeprefix("@")

            body_text = owner.get_text(" ", strip=True)
            if body_text:
                # Prefer visible text if present
                player_name = clean_text(body_text) or player_name

        if not character_name or not player_name:
            continue

        key = (player_name, character_name)
        if key in seen:
            continue

        seen.add(key)
        players.append({
            "player_name": player_name,
            "character_name": character_name,
        })

    return players


def extract_players_from_scripts(soup: BeautifulSoup) -> list[dict[str, str]]:
    """
    Extract participant character/player pairs from embedded script data.
    """
    html = str(soup)

    participant_pattern = re.compile(
        r'"character":\{[^{}]*?"name":"([^"]+)"(?:.|\n)*?"user":\{[^{}]*?"name":"([^"]+)"',
        re.DOTALL,
    )

    players: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for match in participant_pattern.finditer(html):
        character_name = clean_text(match.group(1))
        player_name = clean_text(match.group(2))

        if not character_name or not player_name:
            continue

        key = (player_name, character_name)
        if key in seen:
            continue

        seen.add(key)
        players.append({
            "player_name": player_name,
            "character_name": character_name,
        })

    return players


def extract_session_from_adventure_page(soup: BeautifulSoup, session_url: str) -> dict[str, Any]:
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

    players = extract_players_from_visible_html(soup)
    if not players:
        players = extract_players_from_scripts(soup)

    return {
        "session_name": session_name,
        "date": session_date,
        "dm": {
            "discord_name": dm_discord,
            "player_name": dm_name,
        },
        "players": players,
        "session_url": session_url,
    }


def main() -> None:
    driver = setup_selenium()

    try:
        adventures_list_soup = get_page_soup(
            driver,
            ADVENTURES_URL,
            output_file="adventures_list.html",
        )

        adventure_links = get_adventure_links(adventures_list_soup)

        if not adventure_links:
            print(json.dumps([], indent=2))
            return

        first_url = adventure_links[0]
        soup = get_page_soup(driver, first_url, output_file="adventure_page.html")

        print("Testing URL:", first_url)

        debug_first_participant_blocks(soup)
        debug_participant_regex(soup)

        print("\nVisible extractor result:")
        print(json.dumps(extract_players_from_visible_html(soup), indent=2))

        print("\nScript extractor result:")
        print(json.dumps(extract_players_from_scripts(soup), indent=2))

    finally:
        driver.quit()

if __name__ == "__main__":
    main()