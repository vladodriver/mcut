import os
import sys
import subprocess
import locale
import gettext

from edl import Edl
from api import Api

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

class Postprocess:
    '''Zpracování střihu z ED listu, vykopírování vystříhaného do nového mkv'''

    def __init__(self, filename):
        self.edl = Edl()  # nahraj třídu Edl
        self.api = Api()  # nahraj třídu Api
        # path to mkvmerge executable for all platforms
        if sys.platform == 'linux' or sys.platform == 'darwin':
            self.mkvmerge_exec = 'mkvmerge'
        elif sys.platform == 'win32':
            self.mkvmerge_exec = 'mkvmerge.exe'

        self.tmp_prefix = '_nocut'  # přidá se do <filename>_prefix.mkv
        if os.path.exists(filename):
            self.filename = filename
        else:
            print(_('Requested file: ') + filename + _(' not found!'))
            sys.exit()
        self.duration = self.api.get_duration(self.filename)
        self.edlname = os.path.splitext(self.filename)[0] + '.edl'
        self.orig_filename = os.path.splitext(self.filename)[0] +\
            self.tmp_prefix + os.path.splitext(self.filename)[1]

        try:
            self.edl.import_edl(self.edlname, self.duration)
            self.edllist = self.edl.imported_edl
        except Exception as er:
            print(_('Failed to import an EDL file - error : ') + str(er))
            sys.exit()

    # Pomocné funkce
    def hour_min_sec(self, seconds):
        '''Konvertuje sekundy do h:m:s'''
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return str(int(h)) + ':' + str(int(m)) + ':' + str(round(s, 2))

    def mkvmerge(self):
        '''Remux video with mkvmerge'''
        if self.duration:  # delku videa je potreba znat
            green_areas = []  # vyhledej green areas
            max_index = len(self.edllist) - 1
            for cut in self.edllist:
                if self.edllist.index(cut) == 0 and cut[0] > 0:  # začína zel.
                    green_areas.append([0, cut[0]])  # 0 az cut[0]
                if self.edllist.index(cut) < max_index:
                    next_cut_index = self.edllist.index(cut) + 1  # cut[1]+next
                    green_areas.append([cut[1],
                        self.edllist[next_cut_index][0]])
                if self.edllist.index(cut) == max_index\
                    and cut[1] < self.duration:
                    green_areas.append([cut[1], self.duration])  # last -> end
            print(_('DEBUG : green areas : ') + str(green_areas))
            if green_areas:
                parts_list = []
                for green in green_areas:
                    time = [self.hour_min_sec(time) for time in green]
                    parts_list.append('+' + str(time[0]) + '-' + str(time[1]))
                    parts = 'parts:' + ','.join(parts_list)
                # prejmenuj na *-orig.mkv
                os.rename(self.filename, self.orig_filename)
                mkvtool_cmd = [self.mkvmerge_exec, self.orig_filename,
                    '--split', parts, '-o', self.filename]
                try:
                    print(mkvtool_cmd)
                    subprocess.Popen(mkvtool_cmd)
                except Exception as er:
                    print(_('Not found mkvmerge program! ') + er.args[1])
            else:
                print(_('Not found the green area to leave !'))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        post = Postprocess(filename)
        post.mkvmerge()
        sys.exit()
    else:
        print(_('You must specify the full path to the video file!'))
        print(_('Usage:\n'))
        print(_('postprocess.py <Full path to the video file>\n'))