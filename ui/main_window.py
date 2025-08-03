import queue
import sys
import threading
from tkinter import messagebox

import customtkinter as ctk
import mysql.connector
import yaml

from config import JINA_API_KEY, PROXY_URL, USER_PROMPT_TEMPLATE
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
        self.user_prompt_template = USER_PROMPT_TEMPLATE

        self.prompts = self.load_prompts()

        self.ui_queue = queue.Queue()
        self.active_threads = 0
        self.lock = threading.Lock()

        self.init_ui()
        self.check_queue()

    def load_prompts(self):
        try:
            with open("prompts.yaml", "r", encoding="utf-8") as f:
                prompts_list = yaml.safe_load(f)
                if not isinstance(prompts_list, list):
                    raise yaml.YAMLError(
                        "The root of prompts.yaml should be a list of objects."
                    )
                prompts_dict = {p["name"]: p["text"] for p in prompts_list}
                return prompts_dict
        except FileNotFoundError:
            messagebox.showerror("Error", "prompts.yaml not found!")
            return {"Default": "Please create a prompts.yaml file."}
        except (yaml.YAMLError, TypeError, KeyError) as e:
            messagebox.showerror(
                "YAML Error",
                f"Error parsing prompts.yaml. Check format: {e}\nIt should be a list of {{'name': ..., 'text': ...}}",
            )
            return {"Error": "Invalid YAML format."}

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
        self.url_entry.grid(row=0, column=1, padx=(10, 5), pady=5, sticky="ew")

        self.paste_button = ctk.CTkButton(
            self.url_frame,
            text="Paste",
            command=self.paste_into_url_entry,
            width=60,
        )
        self.paste_button.grid(row=0, column=2, padx=(0, 10), pady=5)

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
        self.use_selenium_check.select()
        self.save_to_excel_check = ctk.CTkCheckBox(
            self.options_frame, text="Save to Excel"
        )
        self.save_to_excel_check.grid(row=0, column=2, padx=10, pady=5)
        self.save_to_excel_check.select()
        self.is_se_check = ctk.CTkCheckBox(
            self.options_frame, text="Input are SE Numbers"
        )
        self.is_se_check.grid(row=0, column=3, padx=10, pady=5)
        self.is_se_check.select()

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

        prompts_tab = self.tab_view.tab("Prompts & Controls")
        prompts_tab.grid_columnconfigure(0, weight=1)
        prompts_tab.grid_rowconfigure(2, weight=1)

        self.prompt_selection_frame = ctk.CTkFrame(prompts_tab)
        self.prompt_selection_frame.grid(
            row=0, column=0, padx=10, pady=(10, 0), sticky="ew"
        )
        self.prompt_selection_frame.grid_columnconfigure(1, weight=1)

        self.prompt_label = ctk.CTkLabel(
            self.prompt_selection_frame, text="Select Prompt:"
        )
        self.prompt_label.grid(row=0, column=0, padx=10, pady=5)

        prompt_names = list(self.prompts.keys())
        self.prompt_menu = ctk.CTkOptionMenu(
            self.prompt_selection_frame,
            values=prompt_names,
            command=self.on_prompt_select,
        )
        self.prompt_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.system_prompt_label = ctk.CTkLabel(prompts_tab, text="System Prompt:")
        self.system_prompt_label.grid(
            row=1, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.system_prompt_edit = ctk.CTkTextbox(prompts_tab, font=("Consolas", 12))
        self.system_prompt_edit.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        self.controls_frame = ctk.CTkFrame(prompts_tab)
        self.controls_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.reset_prompt_btn = ctk.CTkButton(
            self.controls_frame,
            text="Reset Prompt",
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

        # Apply robust, cross-platform shortcuts to all text entry widgets
        self._force_bind_shortcuts(self.url_entry)
        self._force_bind_shortcuts(self.proxy_entry)
        self._force_bind_shortcuts(self.system_prompt_edit)
        self._force_bind_shortcuts(self.raw_md_area)
        self._force_bind_shortcuts(self.processed_area)

        if prompt_names:
            self.on_prompt_select(prompt_names[0])

    def paste_into_url_entry(self):
        """Pastes content from the clipboard into the URL entry widget."""
        try:
            self.url_entry.insert(ctk.INSERT, self.clipboard_get())
        except ctk.TclError:
            # This can happen if the clipboard is empty or contains non-text data
            pass

    def on_prompt_select(self, selected_prompt_name):
        prompt_text = self.prompts.get(selected_prompt_name, "")
        self.system_prompt_edit.delete("1.0", "end")
        self.system_prompt_edit.insert("1.0", prompt_text)

    def _force_bind_shortcuts(self, widget):
        """
        A robust, cross-platform implementation of keyboard shortcuts.
        This is the definitive, final solution. It bypasses buggy virtual
        events by manually checking keys and performing actions directly.
        """
        is_mac = sys.platform == "darwin"
        modifier = "Command" if is_mac else "Control"

        def do_paste(_=None):
            try:
                widget.insert(ctk.INSERT, self.clipboard_get())
            except ctk.TclError:
                pass
            return "break"

        def do_copy(_=None):
            try:
                selected_text = widget.get(ctk.SEL_FIRST, ctk.SEL_LAST)
                self.clipboard_clear()
                self.clipboard_append(selected_text)
            except ctk.TclError:
                pass
            return "break"

        def do_cut(_=None):
            do_copy()
            try:
                widget.delete(ctk.SEL_FIRST, ctk.SEL_LAST)
            except ctk.TclError:
                pass
            return "break"

        def do_select_all(_=None):
            if isinstance(widget, ctk.CTkTextbox):
                widget.tag_add(ctk.SEL, "1.0", "end")
            elif isinstance(widget, ctk.CTkEntry):
                widget.select_range(0, "end")
            return "break"

        widget.bind(f"<{modifier}-v>", do_paste)
        widget.bind(f"<{modifier}-V>", do_paste)
        widget.bind(f"<{modifier}-c>", do_copy)
        widget.bind(f"<{modifier}-C>", do_copy)
        widget.bind(f"<{modifier}-x>", do_cut)
        widget.bind(f"<{modifier}-X>", do_cut)
        widget.bind(f"<{modifier}-a>", do_select_all)
        widget.bind(f"<{modifier}-A>", do_select_all)

    def toggle_proxy_entry(self):
        state = "normal" if self.use_proxy_check.get() else "disabled"
        self.proxy_entry.configure(state=state)
        self.proxy_label.configure(state=state)

    def reset_system_prompt(self):
        selected_prompt_name = self.prompt_menu.get()
        self.on_prompt_select(selected_prompt_name)

    def start_fetch_threads(self):
        inputs = self.url_entry.get("1.0", "end-1c").splitlines()
        inputs = [i.strip() for i in inputs if i.strip()]

        if not inputs:
            messagebox.showerror("Error", "Please provide at least one input.")
            return

        self.process_btn.configure(state="disabled")
        self.update_status("Starting processing...")

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
            except mysql.connector.Error as e:
                messagebox.showerror(
                    "Database Error", f"Failed to get URLs from SE numbers: {e}"
                )
                self.process_btn.configure(state="normal")
                return
            except (ValueError, Exception) as e:
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
                domain=task_info.get("domain"),
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
                    domain=task_info.get("domain"),
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


if __name__ == "__main__":
    app = JinaMDProcessor()
    app.mainloop()
