import customtkinter as ctk
from yami.music import MusicPlayer

print("MusicPlayer imported successfully")

# Create a music player instance
app = MusicPlayer()
print("MusicPlayer instance created")

# Run the main loop
app.mainloop()
print("Mainloop exited")