import tkinter as tk
from tkinter import simpledialog, messagebox
import subprocess
import sys
import psutil
import os
import requests

# --- Window setup ---
root = tk.Tk()
root.title("3D Sandbox game - 774")
root.geometry("300x150")
root.configure(bg="#161321")

accent = "#d9b8ff"
text_color = "#ffffff"

tk.Label(root, text="PyCraft Multiplayer", bg="#161321", fg=accent,
         font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))

status_label = tk.Label(root, text="Checking server...", bg="#161321", fg=text_color)
status_label.pack(pady=(0, 10))


def is_server_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any("pycraft_server.py" in s for s in proc.info['cmdline']):
                return True
        except:
            continue
    return False


def update_status():
    try:
        if is_server_running():
            status_label.config(text="Server is running ✅", fg="green")
        else:
            status_label.config(text="Server is not running ❌", fg="red")
    except Exception as e:
        status_label.config(text=f"Error: {e}", fg="yellow")
    root.after(3000, update_status)


update_status()


def start_server():
    server_path = os.path.join(os.getcwd(), "pycraft_server.py")
    if not os.path.exists(server_path):
        messagebox.showerror("Error", f"{server_path} not found!")
        return
    subprocess.Popen([sys.executable, server_path])


tk.Button(root, text="Start Server", bg="#3a3242", fg=accent,
          command=start_server).pack(pady=5, fill=tk.X, padx=20)


# -------------------------------
# NEW: Auto-detect ngrok IP + PORT
# -------------------------------
def get_ngrok_address():
    try:
        res = requests.get("http://127.0.0.1:4040/api/tunnels").json()
        for t in res.get("tunnels", []):
            if t.get("public_url", "").startswith("tcp://"):
                url = t["public_url"].replace("tcp://", "")
                ip, port = url.split(":")
                return ip, port
    except:
        pass
    return "SERVER OFFLINE", "SERVER OFFLINE"


# -----------------------------------------------------------
# UPDATED Start Client → launches your NEW game script instead
# -----------------------------------------------------------
def start_client():
    username = simpledialog.askstring("Username", "Enter your username:")
    if not username:
        return

    ip, port = get_ngrok_address()

    # CHANGE THIS FILE NAME IF NEEDED
    game_path = os.path.join(os.getcwd(), "client.py")

    if not os.path.exists(game_path):
        messagebox.showerror("Error", f"{game_path} not found!")
        return

    # Launch your new Ursina game
    subprocess.Popen([
        sys.executable,
        game_path,
        "--username", username,
        "--server-ip", ip,
        "--server-port", port
    ])


tk.Button(root, text="Start Client", bg="#3a3242", fg=accent,
          command=start_client).pack(pady=5, fill=tk.X, padx=20)

root.mainloop()
