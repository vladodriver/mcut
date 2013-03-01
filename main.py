#!/usr/bin/env python
import os
import sys
import locale
import gettext
import os
from gui import Gui

locale.setlocale(locale.LC_ALL, '') # use user's preferred locale
# take first two characters of country code
loc = locale.getlocale()
filename = "locales/{}.mo".format(locale.getlocale()[0][0:2])

try:
    print( "Opening message file {} for locale {}".format(filename, loc[0]))
    trans = gettext.GNUTranslations(open( filename, "rb" ))
except IOError:  # file not found
    print( "Locale not found. Using default messages" )
    trans = gettext.NullTranslations()

trans.install()

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
