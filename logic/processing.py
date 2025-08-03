import os
import time
from datetime import datetime

import openpyxl
import requests
import undetected_chromedriver as uc
from g4f.client import Client
from markdownify import markdownify as md

DATA_DIR = "data/results"


def save_to_excel(
    url,
    md_content,
    processed_content,
    source_id=None,
    source_estate_id=None,
    domain=None,
):
    """Saves the provided data to a timestamped Excel file in the data/results directory."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        excel_file = os.path.join(DATA_DIR, f"{timestamp}.xlsx")

        write_header = not os.path.exists(excel_file)

        if write_header:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Processed Data"
            sheet.append(
                [
                    "Domain",
                    "Source Estate ID",
                    "Source ID",
                    "URL",
                    "Raw Markdown",
                    "Processed Content",
                ]
            )
        else:
            workbook = openpyxl.load_workbook(excel_file)
            sheet = workbook.active

        sheet.append(
            [domain, source_estate_id, source_id, url, md_content, processed_content]
        )
        workbook.save(excel_file)
        return True, f"Saved to {excel_file}"
    except Exception as e:
        return False, f"Failed to save to Excel: {e}"


def fetch_md(
    listing_url,
    api_key,
    use_proxy,
    proxy_url,
    ui_queue,
    user_prompt_template,
    system_prompt_text,
    save_excel,
    source_id=None,
    source_estate_id=None,
    domain=None,
):
    if not listing_url:
        ui_queue.put(("error", "Please enter a listing URL"))
        ui_queue.put(("enable_button", True))
        return

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if use_proxy and proxy_url:
            headers["X-Proxy-Url"] = proxy_url

        response = requests.get(
            f"https://r.jina.ai/{listing_url}", headers=headers, timeout=30
        )

        if response.status_code == 200:
            md_content = response.text
            ui_queue.put(("update_text", ("raw", md_content)))

            processed_text = process_md(
                md_content, user_prompt_template, system_prompt_text
            )
            ui_queue.put(("update_text", ("processed", processed_text)))

            status_message = "Completed successfully"
            if save_excel:
                success, message = save_to_excel(
                    listing_url,
                    md_content,
                    processed_text,
                    source_id,
                    source_estate_id,
                    domain,
                )
                status_message += f" | {message}"
                if not success:
                    ui_queue.put(("error", message))

            ui_queue.put(("update_status", status_message))

        else:
            error_msg = f"API Error {response.status_code}: {response.text}"
            ui_queue.put(("error", error_msg))
            ui_queue.put(("update_text", ("raw", error_msg)))

    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        ui_queue.put(("error", error_msg))
        ui_queue.put(("update_text", ("raw", error_msg)))
    finally:
        ui_queue.put(("enable_button", True))


def fetch_md_selenium(
    listing_url,
    api_key,
    use_proxy,
    proxy_url,
    ui_queue,
    user_prompt_template,
    system_prompt_text,
    save_excel,
    source_id=None,
    source_estate_id=None,
    domain=None,
):
    if not listing_url:
        ui_queue.put(("error", "Please enter a listing URL"))
        ui_queue.put(("enable_button", True))
        return

    driver = None
    try:
        chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument('''--headless''')
        chrome_options.add_argument("--disable-gpu")

        if use_proxy and proxy_url:
            chrome_options.add_argument(f"--proxy-server={proxy_url}")

        driver = uc.Chrome(options=chrome_options, use_subprocess=True)
        driver.get(listing_url)
        time.sleep(5)

        html_content = driver.page_source
        md_content = md(html_content)

        ui_queue.put(("update_text", ("raw", md_content)))

        processed_text = process_md(
            md_content, user_prompt_template, system_prompt_text
        )
        ui_queue.put(("update_text", ("processed", processed_text)))

        status_message = "Completed successfully via Selenium"
        if save_excel:
            success, message = save_to_excel(
                listing_url,
                md_content,
                processed_text,
                source_id,
                source_estate_id,
                domain,
            )
            status_message += f" | {message}"
            if not success:
                ui_queue.put(("error", message))

        ui_queue.put(("update_status", status_message))

    except Exception as e:
        error_msg = f"Selenium failed: {str(e)}"
        ui_queue.put(("error", error_msg))
        ui_queue.put(("update_text", ("raw", error_msg)))
    finally:
        if driver:
            driver.quit()
        ui_queue.put(("enable_button", True))


def process_md(raw_md, user_prompt_template, system_prompt_text):
    client = Client()
    system_prompt = system_prompt_text.strip()
    user_prompt = user_prompt_template.format(content=raw_md)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, web_search=False
    )
    return response.choices[0].message.content
