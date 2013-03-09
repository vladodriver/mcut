#!/usr/bin/env python
import os
import sys

from gui import Gui
from translate import Translate

translate = Translate()

if __name__ == '__main__':
    ap = Gui()  # natahni tridu grafiky
    print(str(sys.argv))
    if len(sys.argv) > 1:  # zadano jmeno souboru
        file = sys.argv[1]
        print(file)
        if os.path.exists(file):
            ap.open_video(filename=file)
        else:
            ap.gprint(_('File path ') + str(file) + _(' not found.'))
    ap.gui.mainloop()  # spustit grafiku
