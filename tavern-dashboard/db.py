import psycopg2
import psycopg2.extensions
import os
from os import environ as ENV
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        dbname=ENV.get('DB_NAME'),
        user=ENV.get('DB_USER'),
        host=ENV.get('DB_HOST')
    )