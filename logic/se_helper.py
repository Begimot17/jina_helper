"""
This module is intended to house the logic for converting SE numbers to URLs.
"""

import mysql.connector

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from logic.models import Task


def get_tasks_from_se_numbers(se_numbers: list[str]) -> list[Task]:
    """
    Takes a list of SE numbers and returns a list of dictionaries.
    Each dictionary should contain 'url' and 'source_id'.
    """
    db_params = {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }
    if not all(db_params.values()):
        raise ValueError(
            "Database configuration is incomplete. Please check your .env file for DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD."
        )
    results = []
    conn = None
    try:
        conn = mysql.connector.connect(**db_params)
        cur = conn.cursor()

        # Prepare the query for MySQL.
        # The %s placeholders are for the mysql.connector library.
        se_numbers_stripped = [se.strip() for se in se_numbers if se.strip()]
        if not se_numbers_stripped:
            return []

        # Create a string of placeholders (%s, %s, %s)
        placeholders = ", ".join(["%s"] * len(se_numbers_stripped))
        # Fetch domain name along with other details. Use LEFT JOIN to be robust.
        query = f"""
                        SELECT id, source_id, url, status, rent_status, subtype
                        FROM source_estates
                        WHERE id IN ({placeholders})
                        """
        query_and_domain = f"""
                SELECT
                    se.id,
                    se.source_id,
                    se.url,
                    se.status, 
                    se.rent_status, 
                    se.subtype,
                    t.name_en,
                    se.type_id,
                    s.name AS domain
                FROM source_estates se
                LEFT JOIN sources s ON se.source_id = s.id
                LEFT JOIN types t ON se.type_id = t.id
                WHERE se.id IN ({placeholders})
                """

        cur.execute(query_and_domain, se_numbers_stripped)
        rows = cur.fetchall()

        for row in rows:
            results.append(
                Task(
                    source_estate_id=row[0],
                    source_id=row[1],
                    url=row[2],
                    status=row[3],
                    rent_status=row[4],
                    subtype=row[5],
                    type=f"{row[6]} - Id={row[7]}",
                    domain=row[8],
                )
            )

        cur.close()
    except mysql.connector.Error:
        raise  # Re-raise the exception to be handled by the UI layer
    finally:
        if conn is not None and conn.is_connected():
            conn.close()

    return results
