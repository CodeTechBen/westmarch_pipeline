'''Extracts data from DND Beyond scraped from westmarches and prepares it for transformation and loading into the database.'''
import logging
from setup import setup_logging, get_db_connection
from dotenv import load_dotenv


load_dotenv()


def main():
    '''Main function to execute the extraction process.'''
    setup_logging()
    conn = get_db_connection()
    logging.info("Database connection established.")

if __name__ == "__main__":
    main()