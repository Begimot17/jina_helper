import queue
import threading
from tkinter import messagebox

import customtkinter as ctk

from config import DEFAULT_SYSTEM_PROMPT, JINA_API_KEY, PROXY_URL, USER_PROMPT_TEMPLATE
from logic.processing import fetch_md, fetch_md_selenium
from logic.se_helper import get_urls_from_se_numbers


class JinaMDProcessor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Jina.ai MD Processor")
        self.geometry("1000x900")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.api_key = JINA_API_KEY
        self.proxy_url = PROXY_URL
        self.default_system_prompt = DEFAULT_SYSTEM_PROMPT
        self.user_prompt_template = USER_PROMPT_TEMPLATE

        self.ui_queue = queue.Queue()
        self.active_threads = 0
        self.lock = threading.Lock()

        self.init_ui()
        self.check_queue()

    def init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.header = ctk.CTkLabel(
            self,
            text="Jina.ai Markdown Processor",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.header.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.url_frame.grid_columnconfigure(1, weight=1)
        self.url_label = ctk.CTkLabel(
            self.url_frame, text="Input (URLs or SE Numbers):"
        )
        self.url_label.grid(row=0, column=0, padx=10, pady=5)
        self.url_entry = ctk.CTkTextbox(self.url_frame, height=100)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.options_frame.grid_columnconfigure(5, weight=1)
        self.use_proxy_check = ctk.CTkCheckBox(
            self.options_frame, text="Use Proxy", command=self.toggle_proxy_entry
        )
        self.use_proxy_check.grid(row=0, column=0, padx=10, pady=5)
        self.use_selenium_check = ctk.CTkCheckBox(
            self.options_frame, text="Use Selenium"
        )
        self.use_selenium_check.grid(row=0, column=1, padx=10, pady=5)
        self.save_to_excel_check = ctk.CTkCheckBox(
            self.options_frame, text="Save to Excel"
        )
        self.save_to_excel_check.grid(row=0, column=2, padx=10, pady=5)
        self.is_se_check = ctk.CTkCheckBox(
            self.options_frame, text="Input are SE Numbers"
        )
        self.is_se_check.grid(row=0, column=3, padx=10, pady=5)

        self.proxy_label = ctk.CTkLabel(self.options_frame, text="Proxy:")
        self.proxy_label.grid(row=0, column=4, padx=10, pady=5)
        self.proxy_entry = ctk.CTkEntry(self.options_frame)
        self.proxy_entry.grid(row=0, column=5, padx=10, pady=5, sticky="ew")
        if self.proxy_url:
            self.proxy_entry.insert(0, self.proxy_url)
            self.use_proxy_check.select()
        self.toggle_proxy_entry()

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.tab_view.add("Prompts & Controls")
        self.tab_view.add("Original Markdown")
        self.tab_view.add("Processed Content")

        self.tab_view.tab("Prompts & Controls").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Prompts & Controls").grid_rowconfigure(1, weight=1)

        self.system_prompt_label = ctk.CTkLabel(
            self.tab_view.tab("Prompts & Controls"), text="System Prompt:"
        )
        self.system_prompt_label.grid(
            row=0, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.system_prompt_edit = ctk.CTkTextbox(
            self.tab_view.tab("Prompts & Controls"), font=("Consolas", 12)
        )
        self.system_prompt_edit.insert("1.0", self.default_system_prompt)
        self.system_prompt_edit.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.controls_frame = ctk.CTkFrame(self.tab_view.tab("Prompts & Controls"))
        self.controls_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.reset_prompt_btn = ctk.CTkButton(
            self.controls_frame,
            text="Reset to Default",
            command=self.reset_system_prompt,
        )
        self.reset_prompt_btn.pack(side="left", padx=10, pady=5)

        self.process_btn = ctk.CTkButton(
            self.controls_frame,
            text="Process Listings",
            command=self.start_fetch_threads,
            font=ctk.CTkFont(weight="bold"),
        )
        self.process_btn.pack(side="right", padx=10, pady=5)

        self.raw_md_area = ctk.CTkTextbox(
            self.tab_view.tab("Original Markdown"), font=("Consolas", 12)
        )
        self.raw_md_area.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.processed_area = ctk.CTkTextbox(
            self.tab_view.tab("Processed Content"), font=("Consolas", 12)
        )
        self.processed_area.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_bar.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self._enable_text_widget_bindings(self.url_entry)
        self._enable_text_widget_bindings(self.proxy_entry)
        self._enable_text_widget_bindings(self.system_prompt_edit)
        self._enable_text_widget_bindings(self.raw_md_area)
        self._enable_text_widget_bindings(self.processed_area)

    def _enable_text_widget_bindings(self, widget):
        widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
        widget.bind("<Control-x>", lambda e: widget.event_generate("<<Cut>>"))
        widget.bind("<Control-a>", lambda e: widget.event_generate("<<SelectAll>>"))

    def toggle_proxy_entry(self):
        state = "normal" if self.use_proxy_check.get() else "disabled"
        self.proxy_entry.configure(state=state)
        self.proxy_label.configure(state=state)

    def reset_system_prompt(self):
        self.system_prompt_edit.delete("1.0", "end")
        self.system_prompt_edit.insert("1.0", self.default_system_prompt)

    def start_fetch_threads(self):
        inputs = self.url_entry.get("1.0", "end-1c").splitlines()
        inputs = [i.strip() for i in inputs if i.strip()]

        if not inputs:
            messagebox.showerror("Error", "Please provide at least one input.")
            return

        self.process_btn.configure(state="disabled")
        self.update_status("Starting processing...")

        # Decide if we need to convert SE numbers to URLs first
        if self.is_se_check.get():
            try:
                self.update_status("Converting SE numbers to URLs...")
                tasks = get_urls_from_se_numbers(inputs)
                if not tasks:
                    messagebox.showerror(
                        "Error", "Could not convert any SE numbers to URLs."
                    )
                    self.process_btn.configure(state="normal")
                    return
            except Exception as e:
                messagebox.showerror(
                    "SE Helper Error", f"Failed to get URLs from SE numbers: {e}"
                )
                self.process_btn.configure(state="normal")
                return
        else:
            tasks = [
                {"url": url, "source_id": None, "source_estate_id": None}
                for url in inputs
            ]

        self.active_threads = len(tasks)
        self.update_status(f"Processing {self.active_threads} items...")

        use_selenium = bool(self.use_selenium_check.get())
        save_to_excel = bool(self.save_to_excel_check.get())

        if use_selenium:
            thread = threading.Thread(
                target=self._run_selenium_task, args=(tasks, save_to_excel), daemon=True
            )
            thread.start()
        else:
            for task in tasks:
                thread = threading.Thread(
                    target=self._run_fetch_task,
                    args=(fetch_md, task, save_to_excel),
                    daemon=True,
                )
                thread.start()

    def _run_fetch_task(self, target_func, task_info, save_to_excel):
        try:
            target_func(
                listing_url=task_info["url"],
                api_key=self.api_key,
                use_proxy=bool(self.use_proxy_check.get()),
                proxy_url=self.proxy_entry.get().strip(),
                ui_queue=self.ui_queue,
                user_prompt_template=self.user_prompt_template,
                system_prompt_text=self.system_prompt_edit.get("1.0", "end-1c"),
                save_excel=save_to_excel,
                source_id=task_info.get("source_id"),
                source_estate_id=task_info.get("source_estate_id"),
            )
        finally:
            with self.lock:
                self.active_threads -= 1

    def _run_selenium_task(self, tasks, save_to_excel):
        try:
            for i, task_info in enumerate(tasks):
                self.ui_queue.put(
                    (
                        "update_status",
                        f"[Selenium] Processing {i + 1}/{len(tasks)}: {task_info['url']}",
                    )
                )
                fetch_md_selenium(
                    listing_url=task_info["url"],
                    api_key=self.api_key,
                    use_proxy=bool(self.use_proxy_check.get()),
                    proxy_url=self.proxy_entry.get().strip(),
                    ui_queue=self.ui_queue,
                    user_prompt_template=self.user_prompt_template,
                    system_prompt_text=self.system_prompt_edit.get("1.0", "end-1c"),
                    save_excel=save_to_excel,
                    source_id=task_info.get("source_id"),
                    source_estate_id=task_info.get("source_estate_id"),
                )
        finally:
            with self.lock:
                self.active_threads = 0

    def check_queue(self):
        try:
            while not self.ui_queue.empty():
                message = self.ui_queue.get_nowait()
                msg_type, data = message
                if msg_type == "update_text":
                    widget_id, content = data
                    if widget_id == "raw":
                        self.raw_md_area.delete("1.0", "end")
                        self.raw_md_area.insert("1.0", content)
                    elif widget_id == "processed":
                        self.processed_area.delete("1.0", "end")
                        self.processed_area.insert("1.0", content)
                elif msg_type == "update_status":
                    self.update_status(data)
                elif msg_type == "error":
                    messagebox.showerror("Error", data)

        except queue.Empty:
            pass
        finally:
            if (
                self.active_threads == 0
                and self.process_btn.cget("state") == "disabled"
            ):
                self.process_btn.configure(state="normal")
                self.update_status("Ready")
            self.after(100, self.check_queue)

    def update_status(self, message):
        self.status_bar.configure(text=message)
