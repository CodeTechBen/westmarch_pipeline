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

def load_sessions(conn: psycopg2.extensions.connection, data: dict[str, list[dict[str, any]]], discord_map: dict[str, int], player_name_map: dict[str, int], dnd_map: dict[str, int]):
    '''Loads session data into the database.'''
    session_map = get_sessions(conn)
    player_map = get_players(conn)
    unique_sessions = dict[str, str]() # type: ignore
    sessions = data.get("sessions", [])
    for session in sessions:
        session_name = session.get("session_name")
        session_date = session.get("date")
        dm_name = session.get("dm_name")
        dm_id = player_map[0].get(dm_name) if dm_name else None
        if session_name and session_name not in unique_sessions:
            unique_sessions[session_name] = {
                "date": session_date,
                "dm_id": dm_id,
                "session_name": session_name
            }

    with conn.cursor() as cur:
        for session_name, session_date, dm_id in unique_sessions.items():
            logging.info(f"Loading session: {session_name}")
            cur.execute("""
                INSERT INTO session (session_name, date, dm_player_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_name) DO UPDATE SET
                    date = EXCLUDED.date,
                    dm_player_id = EXCLUDED.dm_player_id
            """, (session_name, session_date, dm_id))
    conn.commit()

def load():
    '''Main function to execute the load process.'''
    setup_logging()
    data = extract()
    logging.info("Data extraction completed. Starting load process.")
    conn = get_db_connection()
    load_players(conn, data["players"])
    discord_map, player_name_map, dnd_map = get_players(conn)

    logging.info("Player lookup maps created successfully.")
    load_races(conn, data)
    load_classes(conn, data)
    class_map = get_classes(conn)
    load_subclasses(conn, data, class_map)
    load_sessions(conn, data, discord_map, player_name_map, dnd_map)

    conn.close()


if __name__ == "__main__":
    load()

    