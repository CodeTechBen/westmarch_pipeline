from os import environ as ENV
import logging
import psycopg2
import psycopg2.extensions

class DatabaseException(Exception):
    pass

def setup_logging(output: str = None, level=logging.INFO): # type: ignore
    '''Sets up logging configuration for the extraction process.'''
    log_date_format = '%Y-%m-%d %H:%M:%S'
    log_format = '{asctime} - {levelname} - {message}'
    if output:
        logging.basicConfig(
            filename=output,
            encoding='utf-8',
            filemode='a',
            level=level,
            format=log_format,
            datefmt=log_date_format,
            style='{'
        )
        logging.info(f"Logging setup complete. Output file: {output}")
    else:
        logging.basicConfig(
            level=level,
            format=log_format,
            datefmt=log_date_format,
            style='{'
        )
    logging.info("Logging setup complete.")

def get_db_connection() -> psycopg2.extensions.connection:
    '''Establishes a connection to the PostgreSQL database using environment variables.'''
    try:
        conn = psycopg2.connect(
            dbname=ENV.get('DB_NAME'),
            user=ENV.get('DB_USER'),
            host=ENV.get('DB_HOST')
        )
        logging.info("Database connection established successfully.")
        return conn
    except DatabaseException as e:
        logging.error(f"Failed to connect to the database: {e}")
        raise

if __name__ == "__main__":
    pass