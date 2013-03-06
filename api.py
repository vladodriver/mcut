import subprocess
import time
import select
import threading
import queue
import sys


class Api:

    def __init__(self):

        '''Vše při startu aplikace - sestavení Gui a spuštění procesu
        -slave Mplayeru'''

        self.out = []  # buffer pro stdout vystupy
        self.position = 0  # aktuální pozice aktuální v sekundách
        self.resp_queue = queue.Queue()  # fronta pro ulozeni pars. odpovedi
        self.duration = 0  # velikost otevřeného videosouboru bez střihu
        self.videofilename = ''  # cesta k aktuálně otevřenému souboru videa
        self.safe_end_time = 0.2  # časová rezerva odečte se od délky videa

        # příkaz api, [příkaz <Mplayeru>, <output True/False>]
        self.cmdlist = {
            'open': ['pausing loadfile', False],  # otevřeni souboru
            'position': ['pausing_keep_force get_time_pos', True],  # pozice
            'seek': ['pausing seek', False],  # +/- s (0)|+/- % (1)|abs. (2)
            'frame_step': ['frame_step', False],  # o 1 frame vpřed
            'pause': ['pause', False],
            'is_paused': ['get_property pause', True],  # vraci 1 kdyz paused
            'stop': ['stop', False],
            'progress': ['pausing osd', False],  # 3 nejvyžší level
            }
        # path to mplayer executable for all platforms
        if sys.platform == 'linux' or sys.platform == 'darwin':
            self.mplayer_exec = 'mplayer'
        elif sys.platform == 'win32':
            self.mplayer_exec = 'mplayer2.exe'
            
        self.mplayer = [self.mplayer_exec, '-quiet', '-slave', '-idle', '-wid']
        self.mp_info_cmd = [self.mplayer_exec, '-identify', '-frames', '0',
        '-vo', 'null', '-ao', 'null']  # mplayer -info cmd

    #***LOGIKA****#

    def start(self, wid):
        '''Spustí Mplayer -slave -quiet -idle mode - wid je předané id
        okna od Gui'''
        self.mplayer.append(wid)
        self.player = subprocess.Popen(self.mplayer, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        self.stdout_thread()
        return True

    def open_video(self, filename):
        # délku videa je třeba zjistit ihned před otevřením
        self.duration = 0  # vynulovat délku
        self.duration = self.get_duration(filename)  # zjistit délku
        self.position = 0  # reset position var to 0
        self.command('open', params=["'" + filename + "'"])
        self.command('progress', [3])  # OSD level 3
        self.videofilename = filename
        
    def stdout_thread(self):
        '''Spustí funkci ge_stdout v samostatnem threadu s timeoutem kvuli
        smycce..'''
        out_thread = threading.Thread(target=self.get_stdout, daemon=True)
        out_thread.start()

    def get_stdout(self, queue=''):
        '''Získá aktuální kousek bufferu a uloží do fronty kdyz je tam
        udaj o pozici'''
        while not self.player.poll():
            line = self.player.stdout.readline().decode()
            if 'ANS_' in line:
                output = line.split('=')[1].replace('\n', '')  # strip newline
                self.resp_queue.put(output)
            else:
                print(line)
                
    # hlavní získávací funkce
    def command(self, command, params=[]):
        '''prijme prikaz pro mplayer typ(get/set, co, parametry)
        viz http://www.mplayerhq.hu/DOCS/tech/slave.txt'''
        if command in self.cmdlist:
            com = self.cmdlist.get(command, '')  # prikaz je v prvnim
            par = ' '.join(map(str, params))  # spoj parametry
            # prikaz je v com[0]
            req = bytes(com[0] + ' ' + par + '\n', 'utf8')
            self.player.stdin.write(req)  # příkaz
            if  com[1] == True:  # com[1] výstup je True
                answ =  self.resp_queue.get(timeout=1)
                return answ
            else:
                return True
                
    def get_duration(self, filename):
        '''Zjisti duration pomoci mplayer --info, jinak nelze korektne
        pretacet'''
        self.mp_info_cmd.append(filename)
        mp_info = subprocess.Popen(self.mp_info_cmd, stdout=subprocess.PIPE,
            bufsize=1)
        info = mp_info.communicate()[0].decode().split('\n')
        duration = ''
        for line in info:
            if 'ID_LENGTH=' in line:
                duration = line.split('=')[1]
                print(_('DEBUG : video length is: ' + duration))
                duration = float(duration)
                if duration > 0:
                    return duration
                elif duration == 0:
                    raise Exception('ValueError',
                    _('Detected video length 0 s video, it may be') +
                    _(' damaged!'))
        if not duration:
            raise Exception('ValueError',
                    _('Unable to identify the video file, it may be') +
                    _(' damaged!'))

    def seek(self, time):
        '''Seekování s rezervou self._end_time tolerance'''
        if time < 0:
            time = 0
            self.position = 0
        elif time > self.duration - self.safe_end_time:
            time = self.duration - self.safe_end_time  # bezpečná rezerva
            self.position = self.duration  # vyžší se počítají jako konec
        self.command('seek', params=[time, 2])

    def framestep(self):
        if self.position <= self.duration - self.safe_end_time:
            self.position = self.duration   # vyžší se počítají jako end
            self.position = self.get_position()  # nova pozice
            self.command('frame_step')

    def get_position(self):
        '''Vypíše pozici potvrzenou Mplayerem a když je
        >= délka - self.safe_end_time vrací plný čas self.duration'''
        try:
            pos = float(self.command('position'))
        except:
            raise Exception('ValueError',
                _('Position not detected, try reload to video file!'))
        if pos >= self.duration - self.safe_end_time:
            pos = self.duration
        return pos

    # ukončení aplikace (zavření okna)
    def close(self):
        self.command('stop')  # zavře soubor v Mplayeru
        self.player.kill()  # zabije subproces Mplayeru)
        return True
