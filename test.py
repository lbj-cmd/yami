import customtkinter as ctk

# Test customtkinter window
ctk.set_default_color_theme("yami/data/theme.json")
ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.title("Test Window")
app.geometry("400x300")

label = ctk.CTkLabel(app, text="CustomTkinter is working!")
label.pack(pady=20)

app.mainloop()