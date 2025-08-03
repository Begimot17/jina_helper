import requests
from g4f.client import Client


def fetch_md(
    listing_url,
    api_key,
    use_proxy,
    proxy_url,
    signal_emitter,
    user_prompt_template,
    system_prompt_text,
):
    """
    Fetches Markdown content from a URL, processes it, and emits signals to update the UI.
    """
    if not listing_url:
        signal_emitter.update_status_signal.emit(
            "Error: Please enter listing URL", True
        )
        signal_emitter.enable_button_signal.emit(True)
        return

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if use_proxy and proxy_url:
            headers["X-Proxy-Url"] = proxy_url
            headers["X-Proxy"] = "auto"

        response = requests.get(
            f"https://r.jina.ai/{listing_url}",
            headers=headers,
            timeout=30,
            verify=False,  # Consider security implications
        )

        if response.status_code == 200:
            md_content = response.text
            signal_emitter.update_text_signal.emit(md_content, "raw")

            processed_text = process_md(
                md_content, user_prompt_template, system_prompt_text
            )
            signal_emitter.update_text_signal.emit(processed_text, "processed")

            signal_emitter.update_status_signal.emit("Completed successfully", False)
        else:
            error_msg = f"API Error {response.status_code}: {response.text}"
            signal_emitter.update_status_signal.emit(error_msg, True)
            signal_emitter.update_text_signal.emit(error_msg, "raw")

    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        signal_emitter.update_status_signal.emit(error_msg, True)
        signal_emitter.update_text_signal.emit(error_msg, "raw")
    finally:
        signal_emitter.enable_button_signal.emit(True)


def process_md(raw_md, user_prompt_template, system_prompt_text):
    """
    Processes the raw Markdown content using an AI model.
    """
    client = Client()
    system_prompt = system_prompt_text.strip()

    # Форматируем пользовательский промпт с подстановкой контента
    user_prompt = user_prompt_template.format(content=raw_md)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, web_search=False
    )
    return response.choices[0].message.content
