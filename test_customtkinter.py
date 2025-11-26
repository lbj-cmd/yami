import customtkinter as ctk
import logging

logging.basicConfig(level=logging.DEBUG)

# Test customtkinter window
print("Initializing customtkinter...")
ctk.set_default_color_theme("yami/data/theme.json")
ctk.set_appearance_mode("dark")

print("Creating window...")
app = ctk.CTk()
app.title("Test Window")
app.geometry("400x300")
app.update_idletasks()

label = ctk.CTkLabel(app, text="CustomTkinter is working!")
label.pack(pady=20)

print("Window created, waiting for mainloop...")
app.mainloop()

print("Mainloop exited.")