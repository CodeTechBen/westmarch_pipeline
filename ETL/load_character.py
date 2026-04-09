# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

'''Loads character data into the database.'''
from .extract_characters import extract
from .setup import get_db_connection, setup_logging

import psycopg2
import logging

def get_players(conn: psycopg2.extensions.connection):
    '''Returns lookup maps for players by different identifiers.'''
    with conn.cursor() as cur:
        cur.execute("SELECT id, discord_name, player_name, dnd_beyond_name FROM players")
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
    player_map = {}
    with conn.cursor() as cur:
        discord_map, player_name_map, dnd_map = get_players(conn)
        for player in players:
            logging.info(f"Loading player: {player['name']}")
            if player['name'] not in player_name_map and player['discord_name'] not in discord_map and player['dnd_beyond_name'] not in dnd_map:
                logging.info(f"Player '{player['name']}' not found in database. Inserting new record.")
                cur.execute("""
                    INSERT INTO players (player_name, discord_name, dnd_beyond_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        player_name = EXCLUDED.player_name,
                        discord_name = EXCLUDED.discord_name,
                        dnd_beyond_name = EXCLUDED.dnd_beyond_name
                    RETURNING id, player_name
                """, (
                    player['name'],
                    player['discord_name'],
                    player['dnd_beyond_name']
                ))
                player_id, player_name = cur.fetchone()
                logging.info("Player data loaded successfully.")
            conn.commit()


def load():
    '''Main function to execute the load process.'''
    setup_logging()
    data = extract()
    logging.info("Data extraction completed. Starting load process.")
    conn = get_db_connection()
    load_players(conn, data["players"])
    discord_map, player_name_map, dnd_map = get_players(conn)
    conn.close()


if __name__ == "__main__":
    load()

    