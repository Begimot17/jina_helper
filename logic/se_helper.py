"""
This module is intended to house the logic for converting SE numbers to URLs.
"""

import mysql.connector


def get_urls_from_se_numbers(se_numbers: list[str]) -> list[dict]:
    """
    Takes a list of SE numbers and returns a list of dictionaries.
    Each dictionary should contain 'url' and 'source_id'.
    """
    db_params = {
        "host": "34.141.182.154",
        "port": "4000",
        "database": "casafari",
        "user": "nikita.dyachkov",
        "password": "jUv6IXpXQN2mT5n6AT93",
    }
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
        query = f"""
                SELECT id, source_id, url
                FROM source_estates
                WHERE id IN ({placeholders})
                """
        # query = f"""
        # SELECT
        #     se.id,
        #     se.source_id,
        #     se.url,
        #     s.name AS domain
        # FROM source_estates se
        # JOIN sources s ON se.source_id = s.id
        # WHERE se.id IN ({placeholders})"""

        cur.execute(query, se_numbers_stripped)
        rows = cur.fetchall()

        for row in rows:
            results.append(
                {
                    "source_estate_id": row[0],
                    "source_id": row[1],
                    "url": row[2],
                    "domain": None,
                }
            )

        cur.close()
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn is not None and conn.is_connected():
            conn.close()

    return results
