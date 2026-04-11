# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

'''Loads character data into the database.'''
from extract_characters import extract
from setup import get_db_connection, setup_logging

import psycopg2
import logging

def get_players(conn: psycopg2.extensions.connection) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    '''Returns lookup maps for players by different identifiers.'''
    with conn.cursor() as cur:
        cur.execute("SELECT player_id, discord_name, player_name, dnd_beyond_name FROM player")
        rows = cur.fetchall()

    discord_map = {}
    player_name_map = {}
    dnd_map = {}

    for row in rows:
        player_id, discord_name, player_name, dnd_name = row

        if discord_name:
            discord_map[discord_name] = player_id
        if player_name:
            player_name_map[player_name] = player_id
        if dnd_name:
            dnd_map[dnd_name] = player_id

    logging.info(f"Loaded {len(rows)} players into lookup maps.")

    return discord_map, player_name_map, dnd_map

def load_players(conn: psycopg2.extensions.connection, players):
    '''Loads player data into the database.'''
    with conn.cursor() as cur:
        discord_map, player_name_map, dnd_map = get_players(conn)
        for player in players:
            logging.info(f"Loading player: {player['player_name']}")
            if player['player_name'] not in player_name_map and player['discord_name'] not in discord_map and player['dnd_beyond_name'] not in dnd_map:
                cur.execute("""
                    INSERT INTO player (player_name, discord_name, dnd_beyond_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (player_id) DO UPDATE SET
                        player_name = EXCLUDED.player_name,
                        discord_name = EXCLUDED.discord_name,
                        dnd_beyond_name = EXCLUDED.dnd_beyond_name
                    RETURNING player_id, discord_name
                """, (
                    player['player_name'],
                    player['discord_name'],
                    player['dnd_beyond_name']
                ))
                player_id, discord_name = cur.fetchone() # type: ignore
                logging.info("Player data loaded successfully.")
            conn.commit()

def get_races(conn: psycopg2.extensions.connection) -> dict[str, int]:
    '''Returns a lookup map for races by name.'''
    with conn.cursor() as cur:
        cur.execute("SELECT race_id, race_name FROM race")
        rows = cur.fetchall()

    race_map = {name: id for id, name in rows}
    logging.info(f"Loaded {len(rows)} races into lookup map.")

    return race_map

def load_races(conn: psycopg2.extensions.connection, data: dict[str, list[dict[str, any]]]):
    '''Loads race data into the database.'''
    race_map = get_races(conn)

    unique_races = dict[str, str]() # type: ignore
    characters = data.get("characters", [])
    for character in characters:
        race = character.get("race")
        race_name = race.get("name") if race else None
        race_description = race.get("description") if race else None
        if race_name and race_name not in unique_races:
            unique_races[race_name] = race_description
        
    with conn.cursor() as cur:
        for race_name, race_description in unique_races.items():
            logging.info(f"Loading race: {race_name}")
            cur.execute("""
                INSERT INTO race (race_name, race_description)
                VALUES (%s, %s)
                ON CONFLICT (race_name) DO UPDATE SET
                    race_description = EXCLUDED.race_description
            """, (race_name, race_description))
    conn.commit()

def get_classes(conn: psycopg2.extensions.connection) -> dict[str, int]:
    '''Returns a lookup map for classes by name.'''
    with conn.cursor() as cur:
        cur.execute("SELECT class_id, class_name FROM class")
        rows = cur.fetchall()

    class_map = {name: id for id, name in rows}
    logging.info(f"Loaded {len(rows)} classes into lookup map.")

    return class_map

def load_classes(conn: psycopg2.extensions.connection, data: dict[str, list[dict[str, any]]]):
    '''Loads class data into the database.'''
    class_map = get_classes(conn)

    unique_classes = dict[str, str]() # type: ignore
    classes = data.get("classes", [])
    for class_info in classes:
        class_name = class_info.get("class_name")
        class_description = class_info.get("description")
        if class_name and class_name not in unique_classes:
            unique_classes[class_name] = class_description

    with conn.cursor() as cur:
        for class_name, class_description in unique_classes.items():
            logging.info(f"Loading class: {class_name}")
            cur.execute("""
                INSERT INTO class (class_name, class_description)
                VALUES (%s, %s)
                ON CONFLICT (class_name) DO UPDATE SET
                    class_description = EXCLUDED.class_description
            """, (class_name, class_description))
    conn.commit()

def get_subclasses(conn: psycopg2.extensions.connection) -> dict[str, int]:
    '''Returns a lookup map for subclasses by name.'''
    with conn.cursor() as cur:
        cur.execute("SELECT subclass_id, subclass_name FROM subclass")
        rows = cur.fetchall()

    subclass_map = {name: id for id, name in rows}
    return subclass_map

def load_subclasses(conn: psycopg2.extensions.connection, data: dict[str, list[dict[str, any]]], class_map: dict[str, int]):
    '''Loads subclass data into the database.'''
    subclass_map = get_subclasses(conn)

    unique_subclasses = dict[str, dict[str, str]]() # type: ignore
    subclasses = data.get("subclasses", [])
    for subclass_info in subclasses:
        subclass_name = subclass_info.get("subclass_name")
        subclass_description = subclass_info.get("description")
        class_name = subclass_info.get("class_name")
        if subclass_name and subclass_name not in unique_subclasses:
            unique_subclasses[subclass_name] = {
                "description": subclass_description,
                "class_name": class_name,
                "class_id": class_map.get(class_name)
            }

    with conn.cursor() as cur:
        for subclass_name, subclass_info in unique_subclasses.items():
            logging.info(f"Loading subclass: {subclass_name}")
            cur.execute("""
                INSERT INTO subclass (subclass_name, subclass_description, class_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (subclass_name) DO UPDATE SET
                    subclass_description = EXCLUDED.subclass_description,
                    class_id = EXCLUDED.class_id
            """, (subclass_name, subclass_info["description"], subclass_info["class_id"]))
    conn.commit()

def get_sessions(conn: psycopg2.extensions.connection) -> dict[str, int]:
    '''Returns a lookup map for sessions by name.'''
    with conn.cursor() as cur:
        cur.execute("SELECT session_id, session_name FROM session")
        rows = cur.fetchall()

    session_map = {name: id for id, name in rows}
    logging.info(f"Loaded {len(rows)} sessions into lookup map.")

    return session_map

def find_existing_player(player: dict[str, str], discord_map: dict[str, int], player_name_map: dict[str, int], dnd_map: dict[str, int]) -> int:
    '''Finds an existing player ID using priority matching.'''

    discord_name = player.get("discord_name")
    player_name = player.get("name")
    dnd_name = player.get("dnd_beyond_name")

    if discord_name and discord_name in discord_map:
        return discord_map[discord_name]

    if player_name and player_name in player_name_map:
        return player_name_map[player_name]

    if dnd_name and dnd_name in dnd_map:
        return dnd_map[dnd_name]

    return None

def load_sessions(
    conn: psycopg2.extensions.connection,
    data: dict[str, list[dict[str, any]]],
    discord_map: dict[str, int],
    player_name_map: dict[str, int],
    dnd_map: dict[str, int]
):
    '''Loads session data into the database.'''

    sessions = data.get("sessions", [])
    unique_sessions: dict[str, dict[str, any]] = {}
    for session in sessions:
        session_name = session.get("session_name")
        session_date = session.get("date")
        dm = session.get("dm", {})

        dm_player = {
            "discord_name": dm.get("discord_name"),
            "name": dm.get("player_name"),
            "dnd_beyond_name": None  
        }

        dm_id = find_existing_player(
            dm_player,
            discord_map,
            player_name_map,
            dnd_map
        )

        if session_name and session_name not in unique_sessions:
            unique_sessions[session_name] = {
                "date": session_date,
                "dm_id": dm_id
            }

    with conn.cursor() as cur:
        for session_name, session_data in unique_sessions.items():
            logging.info(f"Loading session: {session_name}")

            cur.execute("""
                INSERT INTO session (session_name, date, dm_player_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_name) DO UPDATE SET
                    date = EXCLUDED.date,
                    dm_player_id = EXCLUDED.dm_player_id
            """, (
                session_name,
                session_data["date"],
                session_data["dm_id"]
            ))

    conn.commit()

def get_characters(conn: psycopg2.extensions.connection) -> dict[str, int]:
    '''Returns a lookup map for characters by name.'''
    with conn.cursor() as cur:
        cur.execute("SELECT character_id, character_key FROM character")
        rows = cur.fetchall()

    character_map = {key: id for id, key in rows}
    # logging.info(f"{character_map}")
    logging.info(f"Loaded {len(rows)} characters into lookup map.")

    return character_map

def load_character(
    conn: psycopg2.extensions.connection,
    characters: list[dict[str, any]],
    discord_map: dict[str, int],
    player_name_map: dict[str, int],
    dnd_map: dict[str, int]
):
    '''Loads character and character_class data into the database.'''

    race_map = get_races(conn)
    class_map = get_classes(conn)
    subclass_map = get_subclasses(conn)

    character_lookup = get_characters(conn)  # key -> id

    with conn.cursor() as cur:

        for character in characters:
            character_key = character.get("character_key")
            if not character_key:
                continue

            player_key = character.get("player_key")

            player_obj = {
                "discord_name": player_key,
                "name": None,
                "dnd_beyond_name": None
            }

            player_id = find_existing_player(
                player_obj,
                discord_map,
                player_name_map,
                dnd_map
            )

            if not player_id:
                logging.warning(f"No player found for character {player_key}")
                continue

            race_name = character.get("race", {}).get("name")
            race_id = race_map.get(race_name)

            if not race_id:
                logging.warning(f"Race not found: {race_name}")
                continue

            if character_key not in character_lookup:
                cur.execute("""
                    INSERT INTO character (
                        character_key,
                        character_name,
                        character_page_url,
                        dnd_beyond_id,
                        player_id,
                        race_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (character_key) DO UPDATE SET
                        character_name = EXCLUDED.character_name,
                        player_id = EXCLUDED.player_id,
                        race_id = EXCLUDED.race_id
                    RETURNING character_id
                """, (
                    character.get("character_key"),
                    character.get("character_name"),
                    character.get("character_page_url"),
                    character.get("dnd_beyond_id"),
                    player_id,
                    race_id
                ))

                character_id = cur.fetchone()[0]
                character_lookup[character.get("character_key")] = character_id

                logging.info(f"Inserted character: {character.get('character_name')}")
            else:
                character_id = character_lookup[character.get("character_key")]

            for cls in character.get("classes", []):
                class_name = cls.get("class_name")
                subclass_name = cls.get("subclass_name")
                level = cls.get("level", 1)

                class_id = class_map.get(class_name)
                subclass_id = subclass_map.get(subclass_name) if subclass_name else None

                if not class_id:
                    logging.warning(f"Class not found: {class_name}")
                    continue

                cur.execute("""
                    INSERT INTO character_class (
                        character_id,
                        class_id,
                        subclass_id,
                        level
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (character_id, class_id) DO UPDATE SET
                        subclass_id = EXCLUDED.subclass_id,
                        level = EXCLUDED.level
                """, (
                    character_id,
                    class_id,
                    subclass_id,
                    level
                ))

    conn.commit()
    logging.info("Character data loaded successfully.")

def attach_classes_to_characters(
    characters: list[dict],
    character_classes: list[dict]
) -> list[dict]:
    '''
    Combines character data with their classes using character_key.
    Returns characters with a "classes" field.
    '''

    character_map = {
        c["character_key"]: c
        for c in characters
    }

    class_map: dict[str, list[dict]] = {}

    for cls in character_classes:
        key = cls.get("character_key")

        if not key:
            logging.warning(f"Missing character_key for class: {cls}")
            continue

        if key not in class_map:
            class_map[key] = []

        class_map[key].append({
            "class_name": cls.get("class_name"),
            "subclass_name": cls.get("subclass_name"),
            "level": cls.get("level")
        })

    output = []

    for key, character in character_map.items():
        character_copy = character.copy()

        character_copy["classes"] = class_map.get(key, [])

        output.append(character_copy)

    return output

def load_character_classes(
    conn,
    characters: list[dict[str, any]]
):
    '''Loads character_class data into the database.'''

    character_map = get_characters(conn)
    class_map = get_classes(conn)
    subclass_map = get_subclasses(conn)

    with conn.cursor() as cur:

        for character in characters:
            character_key = character.get("character_key")
            character_name = character.get("character_name")
            classes = character.get("classes", [])

            if not character_key or not classes:
                logging.warning(f"Missing character key or classes for character: {character}")
                continue

            character_id = character_map.get(character_key)

            if not character_id:
                logging.warning(f"Character not found in DB: {character_name}")
                continue

            for cls in classes:
                class_name = cls.get("class_name")
                subclass_name = cls.get("subclass_name")
                level = cls.get("level", 1)

                class_id = class_map.get(class_name)
                subclass_id = subclass_map.get(subclass_name) if subclass_name else None

                if not class_id:
                    logging.warning(f"Class not found: {class_name}")
                    continue

                cur.execute("""
                    INSERT INTO character_class (
                        character_id,
                        class_id,
                        subclass_id,
                        level
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (character_id, class_id)
                    DO UPDATE SET
                        subclass_id = EXCLUDED.subclass_id,
                        level = EXCLUDED.level
                """, (
                    character_id,
                    class_id,
                    subclass_id,
                    level
                ))

                logging.info(
                    f"Loaded class for {character_name}: {class_name} ({subclass_name}) lvl {level}"
                )

    conn.commit()
    logging.info("Character classes loaded successfully.")

def build_character_key_lookup(
    characters: list[dict],
    conn
) -> dict[str, int]:
    '''
    Maps character_key -> character_id using character_name as bridge.
    '''

    db_character_map = get_characters(conn)

    lookup = {}

    for c in characters:
        key = c.get("character_key")
        logging.info(f"Processing character for lookup: {key}")
        name = c.get("character_name")
        logging.info(f"Character name for lookup: {name}")

        if not key or not name:
            logging.warning(f"Missing key or name for character: {c}")
            continue

        character_id = db_character_map.get(key)

        if not character_id:
            logging.warning(f"Character not found in DB for key {key}: {name}")
            continue

        lookup[key] = character_id
        logging.info(f"Character key lookup added: {key} -> {character_id}")

    return lookup

def build_session_key_lookup(
    sessions: list[dict],
    conn
) -> dict[str, int]:
    '''
    Maps session_key -> session_id using session_name as bridge.
    '''

    # DB: session_name -> id
    db_session_map = get_sessions(conn)

    lookup = {}

    for s in sessions:
        key = s.get("session_key")
        name = s.get("session_name")

        if not key or not name:
            continue

        session_id = db_session_map.get(name)

        if not session_id:
            logging.warning(f"Session not found in DB for key {key}: {name}")
            continue

        lookup[key] = session_id

    return lookup

def load_character_growth(
    conn,
    characters: list[dict],
    sessions: list[dict],
    character_growth: list[dict]
):
    """Loads character growth data into the database."""

    character_lookup = build_character_key_lookup(characters, conn)
    session_lookup = build_session_key_lookup(sessions, conn)

    with conn.cursor() as cur:

        for growth in character_growth:

            character_key = growth.get("character_key")
            session_key = growth.get("session_key")

            character_id = character_lookup.get(character_key)
            session_id = session_lookup.get(session_key)

            if character_id is None:
                logging.warning(f"Missing character_id for key: {character_key}")
                continue

            if session_key and session_id is None:
                logging.warning(f"Missing session_id for key: {session_key}")
                continue

            cur.execute("""
                INSERT INTO character_growth (
                    character_id,
                    session_id,
                    level,
                    strength,
                    dexterity,
                    constitution,
                    intelligence,
                    wisdom,
                    charisma,
                    hit_points,
                    gold,
                    passive_perception,
                    armor_class
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (character_id, session_id)
                DO UPDATE SET
                    level = EXCLUDED.level,
                    strength = EXCLUDED.strength,
                    dexterity = EXCLUDED.dexterity,
                    constitution = EXCLUDED.constitution,
                    intelligence = EXCLUDED.intelligence,
                    wisdom = EXCLUDED.wisdom,
                    charisma = EXCLUDED.charisma,
                    hit_points = EXCLUDED.hit_points,
                    gold = EXCLUDED.gold,
                    passive_perception = EXCLUDED.passive_perception,
                    armor_class = EXCLUDED.armor_class,
                    time = CURRENT_TIMESTAMP
            """, (
                character_id,
                session_id,
                growth.get("level"),
                growth.get("strength"),
                growth.get("dexterity"),
                growth.get("constitution"),
                growth.get("intelligence"),
                growth.get("wisdom"),
                growth.get("charisma"),
                growth.get("hit_points"),
                growth.get("gold", 0),
                growth.get("passive_perception"),
                growth.get("armor_class")
            ))

    conn.commit()
    logging.info("Character growths loaded successfully.")

def get_tags(conn):
    '''Returns a lookup map for tags by name.'''
    with conn.cursor() as cur:
        cur.execute("SELECT tag_id, tag_name FROM tag")
        rows = cur.fetchall()

    tag_map = {name: id for id, name in rows}
    logging.info(f"Loaded {len(rows)} tags into lookup map.")

    return tag_map

def load_tags(conn, spells, items):
    '''Loads tags for spells and items into the database.'''
    tags = set()
    for spell in spells or []:
        for tag in spell.get("tags", []):
            tags.add(tag)
    for item in items or []:
        for tag in item.get("tags", []):
            tags.add(tag)

    with conn.cursor() as cur:
        for tag in tags:
            logging.info(f"Loading tag: {tag}")
            cur.execute("""
                INSERT INTO tag (tag_name)
                VALUES (%s)
                ON CONFLICT (tag_name) DO NOTHING
            """, (tag,))
    conn.commit()
    logging.info("Tags loaded successfully.")

def load_spells(conn, spells, tag_map):
    '''Loads spell data into the database.'''
    with conn.cursor() as cur:
        for spell in spells or []:
            logging.info(f"Loading spell: {spell.get('spell_name')}")
            range = spell.get("range")
            if range.get("origin") == "self":
                range_value = "Self"
            else:
                range_value = range.get("rangeValue")
            
            duration = spell.get("duration")
            duration_value = " ".join([str(duration.get("durationInterval", "")), duration.get("durationUnit", "")]) if duration else None
            cur.execute("""
                INSERT INTO spell (
                    spell_name,
                    description,
                    level,
                    school,
                    casting_time,
                    range,
                    damage,
                    consumes_material,
                    material_components,
                    duration,
                    is_concentration,
                    is_ritual
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (spell_name) DO UPDATE SET
                    description = EXCLUDED.description,
                    level = EXCLUDED.level,
                    school = EXCLUDED.school,
                    casting_time = EXCLUDED.casting_time,
                    range = EXCLUDED.range,
                    damage = EXCLUDED.damage,
                    consumes_material = EXCLUDED.consumes_material,
                    material_components = EXCLUDED.material_components,
                    duration = EXCLUDED.duration,
                    is_concentration = EXCLUDED.is_concentration,
                    is_ritual = EXCLUDED.is_ritual
            """, (
                spell.get("spell_name"),
                spell.get("description"),
                spell.get("level"),
                spell.get("school"),
                spell.get("casting_time"),
                range_value,
                spell.get("damage"),
                spell.get("consumes_material", False),
                spell.get("material_components"),
                duration_value,
                spell.get("is_concentration", False),
                spell.get("is_ritual", False)
            ))

            cur.execute("""
                SELECT spell_id FROM spell WHERE spell_name = %s
            """, (spell.get("spell_name"),))
            spell_id = cur.fetchone()[0]

            for tag in spell.get("tags", []):
                tag_id = tag_map.get(tag)
                if tag_id:
                    cur.execute("""
                        INSERT INTO spell_tag (spell_id, tag_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (spell_id, tag_id))

    conn.commit()
    logging.info("Spells loaded successfully.")

def load_items(conn, items, tag_map):
    '''Loads item data into the database.'''
    with conn.cursor() as cur:
        for item in items or []:
            logging.info(f"Loading item: {item.get('item_name')}")
            cur.execute("""
                INSERT INTO item (
                    item_name,
                    type,
                    rarity,
                    is_magical
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (item_name) DO UPDATE SET
                    type = EXCLUDED.type,
                    rarity = EXCLUDED.rarity,
                    is_magical = EXCLUDED.is_magical
            """, (
                item.get("item_name"),
                item.get("type"),
                item.get("rarity"),
                item.get("is_magical", False)
            ))

            cur.execute("""
                SELECT item_id FROM item WHERE item_name = %s
            """, (item.get("item_name"),))
            item_id = cur.fetchone()[0]

            for tag in item.get("tags", []):
                item.get("weight"),
                item.get("cost")
            

            cur.execute("""
                SELECT item_id FROM item WHERE item_name = %s
            """, (item.get("item_name"),))
            item_id = cur.fetchone()[0]

            for tag in item.get("tags", []):
                tag_id = tag_map.get(tag)
                if tag_id:
                    cur.execute("""
                        INSERT INTO item_tag (item_id, tag_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (item_id, tag_id))

    conn.commit()

def load():
    setup_logging()

    data = extract()

    conn = get_db_connection()

    load_players(conn, data["players"])
    discord_map, player_name_map, dnd_map = get_players(conn)

    load_races(conn, data)
    load_classes(conn, data)
    class_map = get_classes(conn)
    load_subclasses(conn, data, class_map)

    load_sessions(conn, data, discord_map, player_name_map, dnd_map)

    load_character(conn, data["characters"], discord_map, player_name_map, dnd_map)
    characters_with_classes = attach_classes_to_characters(
    data["characters"],
    data["character_class"]
    )

    load_character_classes(conn, characters_with_classes)

    load_character_growth(
        conn,
        data["characters"],
        data["sessions"],
        data["character_growth"]
    )

    load_tags(conn, data.get('spells'), data.get('items'))
    load_spells(conn, data.get('spells'), get_tags(conn))
    load_items(conn, data.get('items'), get_tags(conn))

    conn.close()


if __name__ == "__main__":
    load()

    