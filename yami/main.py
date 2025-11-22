"""Console entry point"""

import logging
from yami.music import MusicPlayer

"""add sys args and logs"""

logging.getLogger().setLevel(logging.DEBUG)


def entry():
    try:
        app = MusicPlayer()
        app.mainloop()
    except Exception as e:
        logging.exception(e)


if __name__ == "__main__":
    entry()
