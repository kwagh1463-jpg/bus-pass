import os
import psycopg2

conn = psycopg2.connect(os.environ.get("DATABASE_URL"))


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")
