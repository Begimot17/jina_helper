import os
import sys

import yaml
from dotenv import load_dotenv

load_dotenv()

JINA_API_KEY = os.getenv("JINA_API_KEY")
PROXY_URL = os.getenv("PROXY_URL")


def load_prompts():
    """Загружает промпты из YAML файла"""
    try:
        with open("prompts.yaml", "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
            return prompts.get("system_prompt", ""), prompts.get("user_prompt", "")
    except Exception as e:
        print(f"Warning: Failed to load prompts: {str(e)}")
        # Значения по умолчанию
        return "You are a helpful assistant.", "Please analyze this content:\n{content}"


if not JINA_API_KEY:
    print("Error: JINA_API_KEY not found in .env file")
    sys.exit(1)

DEFAULT_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE = load_prompts()
