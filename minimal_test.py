import customtkinter as ctk

print("CustomTkinter imported successfully")

# Create a simple window
root = ctk.CTk()
root.geometry("400x300")
root.title("Minimal Test")

# Add a label
label = ctk.CTkLabel(root, text="Hello, CustomTkinter!")
label.pack(pady=50)

print("Window created, starting mainloop")
root.mainloop()
print("Mainloop exited")