import os
from datetime import datetime

import openpyxl
import requests
import undetected_chromedriver as uc
from g4f.client import Client
from markdownify import markdownify as md
from selenium.common.exceptions import WebDriverException

from logic.models import ProcessingContext, Task

DATA_DIR = "data/results"

# Instantiate the client once at the module level for reuse and performance.
g4f_client = Client()


def save_to_excel(
    task: Task,
    md_content,
    processed_content,
):
    """Saves the provided data to a daily Excel file in the data/results directory."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # Use a daily file to group results from the same day.
        timestamp = datetime.now().strftime("%Y-%m-%d")
        excel_file = os.path.join(DATA_DIR, f"results_{timestamp}.xlsx")

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
                    "Processed Content",
                ]
            )
        else:
            workbook = openpyxl.load_workbook(excel_file)
            sheet = workbook.active

        sheet.append(
            [
                task.domain,
                task.source_estate_id,
                task.source_id,
                task.url,
                processed_content,
            ]
        )
        workbook.save(excel_file)
        return True, f"Saved to {os.path.basename(excel_file)}"
    except (IOError, openpyxl.utils.exceptions.InvalidFileException) as e:
        return False, f"Failed to save to Excel: {e}"
    except Exception as e:
        return False, f"An unexpected error occurred while saving to Excel: {e}"


def _process_and_save_markdown(
    md_content: str,
    task: Task,
    context: ProcessingContext,
    success_message_prefix: str,
):
    """Helper to process MD, update UI, and save results."""
    context.ui_queue.put(("update_text", ("raw", md_content)))

    processed_text = process_md(
        md_content, context.user_prompt_template, context.system_prompt_text
    )
    context.ui_queue.put(("update_text", ("processed", processed_text)))

    status_message = success_message_prefix
    if context.save_excel:
        success, message = save_to_excel(task, md_content, processed_text)
        status_message += f" | {message}"
        if not success:
            context.ui_queue.put(("error", message))

    context.ui_queue.put(("update_status", status_message))


def fetch_md(task: Task, context: ProcessingContext):
    """Fetches markdown content using the Jina Reader API."""
    if not task.url:
        context.ui_queue.put(("error", "Encountered a task with no URL."))
        return

    try:
        headers = {
            "Authorization": f"Bearer {context.api_key}",
            "Content-Type": "application/json",
        }

        if context.use_proxy and context.proxy_url:
            headers["X-Proxy-Url"] = context.proxy_url
            headers["X-Exclude-Selector"] = 'header, footer, nav, aside, script, style, noscript,.header,.footer,.nav,.menu,.sidebar,.ads,.advertisement,.social,.breadcrumbs,.comments,.related,.popup,.subscribe,.newsletter,.cookie,.btn,.icon,.image,.photo,.gallery,.share'

        response = requests.get(
            f"https://r.jina.ai/{task.url}", headers=headers, timeout=30
        )

        if response.status_code == 200:
            md_content = response.text
            _process_and_save_markdown(
                md_content, task, context, "Completed successfully"
            )
        else:
            error_msg = f"API Error {response.status_code}: {response.text}"
            context.ui_queue.put(("error", error_msg))
            context.ui_queue.put(("update_text", ("raw", error_msg)))

    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        context.ui_queue.put(("error", error_msg))
        context.ui_queue.put(("update_text", ("raw", error_msg)))


def fetch_md_selenium(task: Task, context: ProcessingContext):
    """Fetches HTML content using Selenium and converts it to markdown."""
    if not task.url:
        context.ui_queue.put(("error", "Encountered a task with no URL."))
        return

    driver = None
    try:
        chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument('''--headless''')
        chrome_options.add_argument("--disable-gpu")

        if context.use_proxy and context.proxy_url:
            chrome_options.add_argument(f"--proxy-server={context.proxy_url}")

        driver = uc.Chrome(options=chrome_options, use_subprocess=True)
        driver.get(task.url)
        # A simple wait for elements to appear.
        # For more complex pages, explicit waits (WebDriverWait) are more robust.
        driver.implicitly_wait(5)

        html_content = driver.page_source
        md_content = md(html_content)

        _process_and_save_markdown(
            md_content,
            task,
            context,
            "Completed successfully via Selenium",
        )

    except (WebDriverException, Exception) as e:
        error_msg = f"Selenium failed: {str(e)}"
        context.ui_queue.put(("error", error_msg))
        context.ui_queue.put(("update_text", ("raw", error_msg)))
    finally:
        if driver:
            driver.quit()


def process_md(raw_md, user_prompt_template, system_prompt_text):
    system_prompt = system_prompt_text.strip()
    user_prompt = user_prompt_template.format(content=raw_md)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = g4f_client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, web_search=False
    )
    return response.choices[0].message.content
