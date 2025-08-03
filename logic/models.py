import queue
from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    """Represents a single item to be processed."""

    url: str
    source_id: Optional[int] = None
    source_estate_id: Optional[int] = None
    domain: Optional[str] = None


@dataclass
class ProcessingContext:
    """Holds all the contextual information needed for a processing run."""

    api_key: str
    use_proxy: bool
    proxy_url: str
    ui_queue: queue.Queue
    user_prompt_template: str
    system_prompt_text: str
    save_excel: bool
