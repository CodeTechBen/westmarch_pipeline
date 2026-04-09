# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

'''Loads character data into the database.'''
from .extract_characters import extract
from .setup import get_db_connection, setup_logging

import psycopg2
import logging

def load_players(conn: psycopg2.extensions.connection, players):
    '''Loads player data into the database.'''
    with conn.cursor() as cur:
        for player in players:
            logging.info(f"Loading player: {player['name']}")
            cur.execute("""
                INSERT INTO players (player_name, discord_name, dnd_beyond_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    discord_name = EXCLUDED.discord_name,
                    dnd_beyond_name = EXCLUDED.dnd_beyond_name
            """, (
                player['name'],
                player['discord_name'],
                player['dnd_beyond_name']
            ))
        conn.commit()
    logging.info("Player data loaded successfully.")

def load():
    '''Main function to execute the load process.'''
    setup_logging()
    data = extract()
    logging.info("Data extraction completed. Starting load process.")
    conn = get_db_connection()
    load_players(conn, data["players"])

if __name__ == "__main__":
    load()

    