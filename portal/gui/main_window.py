"""
Portal main window — environment toggle, action list, credentials button.
"""
import sys
import tkinter as tk
from tkinter import ttk

import defaults_manager as dm
from portal.credentials import credential_manager as cm
from portal.gui.credentials_dialog import CredentialsDialog
from portal.gui.action_window import MembersListWindow
from portal.gui.delete_users_window import DeleteUsersWindow
from portal.gui.db_extract_window import DbExtractWindow
from portal.gui.post_event_window import PostEventWindow
from portal.actions.members_list_action import MembersListAction
from portal.actions.delete_users_action import DeleteUsersAction
from portal.actions.db_extract_action import DbExtractAction
from portal.actions.post_event_action import PostEventAction


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yedidya Admin Portal")
        self.resizable(False, False)
        self.minsize(380, 220)

        # Environment: load from config, default to 'staging'
        saved_env = dm.get('portal', 'environment')
        self._env = tk.StringVar(value=saved_env if saved_env in ('staging', 'production') else 'staging')
        self._env.trace_add('write', self._on_env_change)

        self._actions = [MembersListAction(), DeleteUsersAction(), DbExtractAction(), PostEventAction()]
        self._build()
        self._check_credentials()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)

        # --- Header bar ---
        header = ttk.Frame(self, padding=(12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Yedidya Admin Portal",
                  font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Update Credentials",
                   command=self._open_settings).grid(row=0, column=1, padx=(8, 0))

        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")

        # --- Environment toggle ---
        env_frame = ttk.Frame(self, padding=(12, 6))
        env_frame.grid(row=2, column=0, sticky="ew")

        ttk.Label(env_frame, text="Environment:").pack(side="left", padx=(0, 8))
        for env in ('staging', 'production'):
            ttk.Radiobutton(
                env_frame, text=env.capitalize(),
                variable=self._env, value=env
            ).pack(side="left", padx=4)

        self._env_label = ttk.Label(env_frame, text="", foreground="#e67e22",
                                    font=("Segoe UI", 9, "bold"))
        self._env_label.pack(side="left", padx=(12, 0))
        self._refresh_env_label()

        ttk.Separator(self, orient="horizontal").grid(row=3, column=0, sticky="ew")

        # --- Actions list ---
        actions_frame = ttk.Frame(self, padding=(12, 8))
        actions_frame.grid(row=4, column=0, sticky="nsew")
        actions_frame.columnconfigure(0, weight=1)

        for i, action in enumerate(self._actions):
            self._action_row(actions_frame, i, action)

        ttk.Separator(self, orient="horizontal").grid(row=5, column=0, sticky="ew")

        # --- Status bar ---
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, foreground="gray",
                  padding=(12, 4)).grid(row=6, column=0, sticky="w")

    def _action_row(self, parent, row, action):
        frame = ttk.Frame(parent, padding=(0, 4))
        frame.grid(row=row, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)

        info = ttk.Frame(frame)
        info.grid(row=0, column=0, sticky="w")
        ttk.Label(info, text=action.name,
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(info, text=action.description,
                  foreground="gray").pack(anchor="w")

        ttk.Button(frame, text="Go",
                   command=lambda a=action: self._run_action(a)).grid(
            row=0, column=1, padx=(8, 0))

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------

    def _on_env_change(self, *_):
        env = self._env.get()
        dm.set_default('portal', 'environment', env)
        self._refresh_env_label()

    def _refresh_env_label(self):
        env = self._env.get()
        if env == 'production':
            self._env_label.configure(text="⚠ PRODUCTION", foreground="#c0392b")
        else:
            self._env_label.configure(text="", foreground="#e67e22")

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def _check_credentials(self):
        env = self._env.get()
        if not cm.has_credentials(env):
            self._status_var.set(f"First run: please enter your {env} credentials.")
            self.after(100, lambda: CredentialsDialog(
                self, on_save=self._on_creds_saved, initial_tab=env))

    def _on_creds_saved(self):
        self._status_var.set("Credentials saved.")

    def _open_settings(self):
        CredentialsDialog(self, on_save=self._on_creds_saved,
                          initial_tab=self._env.get())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _run_action(self, action):
        env = self._env.get()
        if not cm.has_credentials(env):
            self._status_var.set(f"Please enter {env} credentials first.")
            CredentialsDialog(self, on_save=self._on_creds_saved, initial_tab=env)
            return
        if isinstance(action, MembersListAction):
            MembersListWindow(self, action, env=env)
        elif isinstance(action, DeleteUsersAction):
            DeleteUsersWindow(self, action, env=env)
        elif isinstance(action, DbExtractAction):
            DbExtractWindow(self, action, env=env)
        elif isinstance(action, PostEventAction):
            PostEventWindow(self, action, env=env)
