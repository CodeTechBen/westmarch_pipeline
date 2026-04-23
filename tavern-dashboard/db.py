import psycopg2
import psycopg2.extensions
import os
from os import environ as ENV
from dotenv import load_dotenv

load_dotenv()

def get_connection(system: str) -> psycopg2.extensions.connection:
    '''Establishes a connection to the PostgreSQL database using environment variables.'''
    if system == "local":

        conn = psycopg2.connect(
            dbname=ENV.get('DB_NAME'),
            user=ENV.get('DB_USER'),
            host=ENV.get('DB_HOST')
        )
        return conn

    else:
        conn = psycopg2.connect(
            dbname=ENV.get("DB_NAME"),
            user=ENV.get("DB_USER"),
            password=ENV.get("DB_PASSWORD"),
            host=ENV.get("DB_HOST"),
            port=ENV.get("DB_PORT", "5432")
        )
        return conn