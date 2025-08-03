import os
import sys

from dotenv import load_dotenv

load_dotenv()

JINA_API_KEY = os.getenv("JINA_API_KEY")
PROXY_URL = os.getenv("PROXY_URL")

# Database credentials
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not JINA_API_KEY:
    print("Error: JINA_API_KEY not found in .env file")
    sys.exit(1)

# The user prompt template. The {content} placeholder will be filled with the markdown.
# This is used by the processing functions.
USER_PROMPT_TEMPLATE = "Please analyze this content:\n{content}"
