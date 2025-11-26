import tkinter as tk
import customtkinter as ctk
from yami.main import entry
import traceback

print("Starting application...")

try:
    # Set customtkinter appearance mode
    ctk.set_appearance_mode("dark")
    
    # Run the application
    entry()
except Exception as e:
    traceback.print_exc()
    input("Press Enter to exit...")
