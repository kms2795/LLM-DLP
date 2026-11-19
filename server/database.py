import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="fhwa.c7saa0uiu5zi.ap-northeast-2.rds.amazonaws.com",
        port=5432,
        database="postgres",
        user="admins",
        password="REMOVED_FOR_SUBMISSION"
    )
    return conn
