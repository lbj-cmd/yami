import tkinter as tk

print("Initializing Tkinter...")
app = tk.Tk()
app.title("Tkinter Test Window")
app.geometry("400x300")
app.update_idletasks()

label = tk.Label(app, text="Tkinter is working!")
label.pack(pady=20)

print("Window created, waiting for mainloop...")
app.mainloop()

print("Mainloop exited.")