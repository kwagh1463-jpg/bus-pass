import psycopg2

DATABASE_URL = "postgresql://postgres:FVy9B1pZB548srnw@db.wthnonfiunrhmvvsszid.supabase.co:5432/postgres"

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")
