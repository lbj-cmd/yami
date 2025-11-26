import customtkinter as ctk
import tkinter as tk
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)

# Test customtkinter window
print("Initializing customtkinter...")
ctk.set_default_color_theme("yami/data/theme.json")
ctk.set_appearance_mode("dark")

print("Creating window...")
app = ctk.CTk()
app.title("Test Window")
app.geometry("800x500")
app.update_idletasks()
app.lift()
app.attributes('-topmost', True)
app.after_idle(app.attributes, '-topmost', False)

# Create simple widgets
label = ctk.CTkLabel(app, text="CustomTkinter Test")
label.pack(pady=20)

button = ctk.CTkButton(app, text="Click Me")
button.pack(pady=10)

print("Window created, waiting for mainloop...")
app.mainloop()

print("Mainloop exited.")