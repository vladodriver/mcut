from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import os

from api import Api
from edl import Edl


class Gui:

    '''Gui pro Mcutter'''

    def __init__(self):
        # třída logiky ovládáni Mplayer api
        self.api = Api()
        # třída pro práci s EDL
        self.edl = Edl()

        # hl.okno titulek a rozmery
        self.gui = Tk()
        self.gui.title(_('Commercial cutter'))
        # při zavření okna
        self.gui.protocol("WM_DELETE_WINDOW", self.close)
        self.gui.bind('<Control-KeyPress-q>', self.close)
        # styl
        if sys.platform == 'linux':
            self.style = ttk.Style()  # fix ugly appearance
            self.style.theme_use('clam')

        # prvky okna od shora dolů
        # video plátno
        self.video = Canvas(self.gui, width=800, height=450)
        self.video.grid(row=0, column=0, columnspan=9, sticky='wens')
        self.video.bind('<Double-Button-1>', self.fullscreen)  # fullscreen
        for event in '<Enter>', '<Leave>':
            self.video.bind(
                event, lambda e,
                help=_('Double click to switch to full screen.'):
                    self.tooltip(e, help))
        # plátno střihu
        self.play_before_cut = 2  # počet sekund ukázky přehrání přesk. reklamy
        self.blink_time = 200  # interval blikání editovaného cutu v ms
        self.cutting = Canvas(self.gui, width=800, height=22, bg='#D9D9D9',
            cursor='hand1', highlightthickness=0)
        self.cutting.grid(row=1, column=0, columnspan=9, sticky='we')
        self.cutting.bind('<Button-1>', self.edit_cut_changer)  # přepinani
        self.gui.bind('<Shift_R>', self.edit_cut_changer)  # přepinani shiftem
        self.cutting.bind('<Button-3>', self.edl_insert_new)  # nový střih
        self.gui.bind('<Return>', self.edl_insert_new)  # --//--
        self.gui.bind('<Escape>', self.deselect_cut)  # nulovani vyberu
        self.gui.bind('<Delete>', self.cut_delete)  # vymazani cutu v edit mode
        self.edl_cuts = []  # analogie k self.edl.edl pro ID cisla střihu obd.
        self.editmode = False  # stav edit mod ano/ne při vybrani cutu
        # plátno progress baru
        self.pbar = Canvas(self.gui, width=800, height=16, bg='#D9D9D9',
            cursor='xterm', highlightthickness=0)
        self.pbar.grid(row=2, column=0, columnspan=9, sticky='we')
        for event in ['<Configure>', '<Button-1>', '<ButtonRelease-1>',
            '<B1-Motion>', '<Button-3>', '<ButtonRelease-3>', '<B3-Motion>']:
            self.pbar.bind(event, self.mouse_set_pos)
        self.pbar.bind('<Configure>', self.redraw_canvas)
        self.progress = ''  # progressbar - modry obdelnik
        self.mouse_soft_pos = False  # proměnná pro jemný posuv True nebo False
        self.click_canvas_pos = 0  # posl. souř. kliku pro e.type 6 (tažení)
        # Message info - stavový řádek
        self.info = Label(
            self.gui, height=0, wraplength=600, bg='#FFFCDD', font="Arial 12")
        self.info.grid(row=5, column=0, columnspan=9, sticky='we')
        # regulace velikost posuvu vpřed/vzad
        self.shift_values = ['0.1 sec. => 0.1', '1 sec. => 1', '5 sec. => 5',
            '10 sec. => 10', '30 sec. => 30', '1 min. => 60', '5 min. => 300',
            '10 min. => 600', '30 min. => 1800']
        # aktuální hodnota posunu v sekundách
        self.shift_actual_value = 30
        # spinbox v Gui
        self.shift = Spinbox(
            values=self.shift_values, cursor='sb_v_double_arrow',
            readonlybackground='#FFFCDD', command=self.set_shift,
            state='readonly', font="Arial 12", justify='center', width=16)
        self.shift.grid(row=3, column=3, columnspan=3, sticky='we')
        for event in '<Up>', '<Down>':
            self.gui.bind(event, self.set_shift)
        for event in '<Button-4>', '<Button-5>':  # kolečko myši up/down
            self.shift.bind(event, self.set_shift)
        # spid a spis seconds/pixels pro duration seconds/pixels pro shift
        self.spid = 0  # poměr pix/sec pro api.duration
        self.spis = self.sec_to_pix_ratio(self.shift_actual_value)
        # tkinter variable ze self.shift_values
        self.shift_spinbox_value = StringVar()  # inicializace tk proměnné
        self.shift_spinbox_value.set('30 sec. => 30')  # nastav vých hodnotu
        self.shift['textvariable'] = self.shift_spinbox_value  # a přiřaď
        # Tooltip pro plátno střihu a velikost přetáčení
        for event in '<Enter>', '<Leave>':
            self.pbar.bind(event,
                lambda e, help=_('Rewind LM + drag - soft RM + drag '):
                    self.tooltip(e, help))
            self.cutting.bind(event,
                lambda e, help=_('Cutting canvas ,') +
                _(' next cut mark [Ctrl] + <- ->, insert new [Enter]/RM') +
                _(' Back Esc/LM/P-Shift'): self.tooltip(e, help))
            self.shift.bind(event,
                lambda e, help=_('Skip shift: more [Up] less [Down] '):
                    self.tooltip(e, help))
        # lcdl - levý lcd + lcdr - pravý lcd
        for lcd in 'lcd_l', 'lcd_r':
            setattr(self, lcd, Label(self.gui, wraplength=600, bg='#FFFCDD',
            font='Arial 12', relief='sunken', justify='center'))
        self.lcd_l.grid(row=3, column=0, columnspan=3, sticky='we')
        self.lcd_l['text'] = _('Cut not selected')
        self.lcd_r.grid(row=3, column=6, columnspan=3, sticky='we')
        self.lcd_r['text'] = _('Video file not open')

        # ikony pro buttony
        self.icon = []  # zásobník na ikony
        for name in ['open.gif', 'import.gif', 'back_cut.gif', 'back.gif',
            'play.gif', 'forw.gif', 'forw_cut.gif', 'framestep.gif',
            'save.gif']:
            self.icon.append(PhotoImage(file="icons/" + name))

        # tlacitka [<text>, <funkce>, <kl.zkratka>, <text nápovědy(tooltip)>]
        self.buttons = [
            ('open_button', ['open_video', '<Control-KeyPress-o>',
                _('Open video file [Ctrl+o]')]),
            ('open_edl_button', ['edl_import', '<Control-KeyPress-i>',
                _('Import cuts  from EDL file [Ctrl+i]')]),
            ('prev_cut_button', ['prew_cut', '<Control-KeyPress-Left>',
                _('Previous cut [Ctrl+Left]')]),
            ('rewind_button', ['rewind', '<Left>',
                _('Fast rewind [Left]')]),
            ('play_button', ['play', '<p>',
                _('Play / pauze or a show of the selected cut [p]')]),
            ('refind_button', ['refind', '<Right>',
                _('Fast forward [Right]')]),
            ('next_cut_button', ['next_cut', '<Control-KeyPress-Right>',
                _('Next cut [Ctrl+Left]')]),
            ('framestep_button', ['framestep', '<f>',
                _('Go one frame forward [f]')]),
            ('save_edl_bbutton', ['save_edl', '<Control-KeyPress-s>',
                _('Save to EDL file [Ctrl+s]')])
            ]

        # buttony
        for button in self.buttons:
            index = self.buttons.index(button)
            #predava se tlacitko, (text, funkce)
            setattr(self, button[0], ttk.Button(self.gui,
                image=self.icon[self.buttons.index(button)],
                command=getattr(self, button[1][0])))
            cudl = getattr(self, button[0])  # cast self.<open_button>
            #Tool tipy v Labelu info
            help = button[1][2]
            for event in '<Enter>', '<Leave>':
                cudl.bind(event, lambda e, help=help: self.tooltip(e, help))
            # + grid
            cudl.grid(row=4, column=index, sticky='we')
            #nast. roztahovat druhý řádek
            self.gui.grid_rowconfigure(0, weight=1)
            #nast. roztahovat tlačítka 4. řádek/ vsechny sloupce
            self.gui.grid_columnconfigure(index, weight=1)
            #Kl. zkratky
            self.gui.bind_all(button[1][1], getattr(self, button[1][0]))

        # start Mplayeru v iddle režimu v okně canvasu při otevření aplikace
        self.wid = str(hex(self.video.winfo_id()))
        self.api.start(self.wid)

    #***FUNKCE OVLADAČŮ UDÁLOSTÍ TLAČÍTKA, KLÁVESY***#

    def tooltip(self, e, help):
        '''Zobrazovač tooltipů v labelu info'''
        if e.type == '7':  # najede mys
            self.info['text'] = help  # tooltip zobraz
        elif e.type == '8':  # mys odjela
            self.info['text'] = ''  # smazat tooltip

    def close(self, e=''):
        '''zavření okna jakymkoliv způsobem'''
        if self.edl.imported_edl != self.edl.edl:  # byly učiněny změny
            save = messagebox.askyesno(_('Save changes ?'),
                _('In the list of cuts made ​​changes,') +
                _(' you want to save them?'))
            if save:
                self.save_edl()
        if self.api.player:
            self.api.close()
        self.gui.destroy()
        print('the END :)')  # grafika už je mrtvá

    def fullscreen(self, e=''):
        '''Prepne aplikaci do fullscreen modu'''
        if self.gui.attributes('-fullscreen') == 0:
                self.gui.attributes('-fullscreen', 1)
        else:
                self.gui.attributes('-fullscreen', 0)

    def open_video(self, e='', filename=''):
        '''Otevření videa'''
        if filename:
            video = filename
        else:
            video = filedialog.askopenfilename(title=_('Select video file'),
                filetypes=[('MKV', '*.mkv'), ('MPEG', '*.mpg'),
                ('AVI', '*.avi')])
        if video:
            try:
                self.edl.edl = []  # reset stareho EDL
                self.edl.imported_edl = []  # reset stareho importovaneho EDL
                self.edl_render(self.edl.edl, method='redraw')  # re-draw
                self.api.open_video(video)  # jaky soubor otevrit
                self.pbar.delete(self.progress)  # vymazat starý progressbar
                self.edl.edl_name(video)  # název edl dle videa
                self.cutting['bg'] = '#008A00'  # barvy
                self.redraw_canvas()  # překreslit a získat spid a spis
                self.editmode = False  # vypnutí edit mode
                self.edl.sel_cut_index = [None, None]  # reset selected cut
                self.lcd_l['text'] = _('Cut unselected')  # reset cut lcd
                # vytvoření prvku progressbar pozice videa
                self.progress = self.pbar.create_rectangle(0, 0, 0, 16,
                    fill='blue', width=0)
                self.actual_position()  # sledovani pozice kazdou vterinu
                # jméno a délka videa titulek a info
                self.gui.title(os.path.split(self.api.videofilename)[1] +
                    ' - ' + _('Commercial cutter'))
                self.gprint('Video: ' + os.path.split(
                    self.api.videofilename)[1] + ' délka: ' +
                    str(self.api.duration))
                # kdyz existuje stejnojmenne edl tak imporovat
                if os.path.exists(self.edl.edlname):
                    self.edl_import(quiet=True)
            except Exception as er:
                messagebox.showerror(_('Error while opening video '),
                    er.args[1])
        else:
            self.gprint(_('The video file was not selected!'))

    def edl_import(self, e='', quiet=False):
        '''otevře EDL pro uživatelský import - quiet je pro import bez dialogu
        na vybrani souboru'''
        if self.api.duration:
            if not quiet:  # quiet True tichy rezim bez dialogu
                edl = filedialog.askopenfilename(
                    title=_('Select the EDL file'),
                    filetypes=[('EDL', '*.edl')])
            elif quiet:
                edl = self.edl.edlname  # když exis. edl ktery ma stejne jmeno
            if edl:
                try:
                    self.edl.import_edl(edl, self.api.duration)  # importovat
                    self.edl.edl = list(self.edl.imported_edl)  # vytv. kopie
                    self.edl_render(self.edl.edl, method='redraw')  # render
                    self.gprint(_('Importing EDL file ') +
                        edl + _(' was successful'))
                except Exception as er:
                    print(self.edl.edl)
                    self.edl.imported_edl = []  # nulování import EDL listu
                    self.edl_render(self.edl.edl, method='redraw')  # render
                    self.gprint(_('EDL file: ') + edl +
                        _(' failed to import - Error: ') + str(er))
            else:
                self.gprint(_('Selecting an EDL file has been canceled'))
        else:
            self.gprint('Please first open video video!')

    def play_previous_cut(self, e=''):
        self.mark_rewinder('back')

    def play_next_cut(self, e=''):
        self.mark_rewinder('next')

    def rewind(self, e=''):
        '''přetáčení vzad'''
        self.rewinder('back')

    def refind(self, e=''):
        '''přetáčení vpřed'''
        self.rewinder('forw')

    def prew_cut(self, e=''):
        self.mark_rewinder('back')

    def next_cut(self, e=''):
        self.mark_rewinder('next')

    def play(self, e=''):
        '''pause/play'''
        if self.api.duration:
            cut_index = self.edl.sel_cut_index[0]
            if cut_index == None:  # normalne play/pause strih neni vybran
                self.api.command('pause')
            else:  # kdyz je vybran cut prehraje se ukazka cutu
                cut_start = self.edl.edl[cut_index][0]  # zacatek preskoku
                if cut_start >= self.play_before_cut:  # sekund hrani pred r.
                    pos_before = cut_start - self.play_before_cut  # zacit -2s
                    self.gui.after(self.play_before_cut * 1000,
                        self.play_after_cut)
                else:
                    pos_before = 0  # hrej od zacatku a preskoc $cut_start sec
                    self.gui.after(int(cut_start * 1000), self.play_after_cut)
                self.api.seek(pos_before)  # pretoc na start ukazky
                self.pos_progress(pos_before)  # pretoc progressbar -//-
                self.api.command('pause')  # zacni hrat
        else:
            self.gprint(_('You do not have any open video!'))

    def play_after_cut(self):
        '''Prehraje ukazku reklamy ...'''
        cut_index = self.edl.sel_cut_index[0]  # zjisti aktualni sel. index
        cut_end = self.edl.edl[cut_index][1]  # konec reklamy
        self.api.seek(cut_end)  # skok za reklamu
        self.pos_progress(cut_end)  # pretoc progressbar
        self.deselect_cut()  # deselectuj cut pro normal play
        if self.api.position < self.api.duration:  # kdyz neni konec videa
            self.play()  # prehravej normalne dal pomoci self.play

    def framestep(self, e=''):
        '''skok o 1 frame'''
        if self.api.duration:
            self.api.framestep()
        else:
            self.gprint(_('You do not have any open video!'))

    def save_edl(self, e=''):
        '''uloží EDL do souboru na žádost uživatele'''

        if self.edl.edlname and self.edl.edl:
            try:
                self.edl.save_edl(self.edl.edlname)
                self.gprint(_('EDL file was saved to: ') + self.edl.edlname)
            except Exception as er:
                self.gprint(_('EDL could not be saved to: ') +
                    self.edl.edlname + ' Error: ' + er)
        else:
            self.gprint(
                _('It is necessary to open a video and perform video cut'))

    def set_shift(self, e=''):
        '''Interval skoku posunu vpřed/vzad pomocí Up/Down'''
        # načte aktuální hodnotu widgetu shift (spinbox)
        shift_index = self.shift_values.index(self.shift_spinbox_value.get())
        if e:  # ovládáno myší nebo Up/Down klávesou
            if e.keysym == 'Up' or e.num == 4:  # nahoru na doraz
                if shift_index < len(self.shift_values) - 1:
                    shift_index += 1
                self.shift_spinbox_value.set(self.shift_values[shift_index])
            elif e and e.keysym == 'Down' or e.num == 5:  # dolu az k 0
                if shift_index > 0:
                    shift_index -= 1
                self.shift_spinbox_value.set(self.shift_values[shift_index])
        # nastaví aktuálni hodnotu posuvu přetáčení dle indexu zvolene hodnoty
        self.shift_actual_value = float(self.shift_values[shift_index].split(
            '=>')[1].strip())
        # rekonfiguruje self.spis sec/shift_actual_value
        self.spis = self.sec_to_pix_ratio(self.shift_actual_value)
        self.gprint(_('Size of shift: ') + str(self.shift_actual_value)
            + ' s - ' + str(self.spis) + ' sec/pixel')

    def mouse_set_pos(self, e):
        '''Pomocí stisknutí Button-1 myši a tažení přetáčí na lib. pozici'''
        if self.api.duration:  # video musí být open
            # reakce na událost dle typu
            if e.type == '4' and e.num == 3:
                self.mouse_soft_pos = True  # přepnutí na jemný Myš 3
                self.click_canvas_pos = e.x  # x je +/- pix od kliku
            elif e.type == '4' and e.num == 1 or e.type == '6' \
                and self.mouse_soft_pos == False:  # nebylo přepnuto na jemny
                self.pbar.itemconfig(self.progress, fill='orange')  # oranzovy
                time_pos = self.spid * e.x  # vypočet time pos
                self.api.seek(time_pos)  # přetočit na
                self.api.position = time_pos  # update pozice v api
                self.pos_progress(time_pos)  # update progressbaru a lcd
                if self.editmode == True:
                    self.edl_cutter(round(self.api.position, 2))
                self.lcd_r['text'] = str(round(time_pos, 2)) + ' s z' +\
                    str(self.api.duration) + ' s'
            elif e.type == '6' and self.mouse_soft_pos == True:  # jemné Myš 3
                self.pbar.itemconfig(self.progress, fill='orange')
                click_pix_diff = e.x - self.click_canvas_pos  # myš +/-
                time_diff = self.spis * click_pix_diff
                time_pos = time_diff + self.api.position
                self.api.seek(time_pos)
                self.pos_progress(time_pos)  # update progressbaru
                if self.editmode == True:
                    self.edl_cutter(round(time_pos, 2))  # pribl. pozice zaokr.
                self.lcd_r['text'] = str(round(time_pos, 2)) + ' s z' +\
                    str(self.api.duration) + ' s'
            elif e.type == '5':  # uvolněno tl. myši resety
                self.pbar.itemconfig(self.progress, fill='blue')  # reset barvy
                try:
                    self.api.position = self.api.get_position()  # presna pozice
                except Exception as er:
                    self.gprint(er.args[1])
                    self.open_video(filename=self.api.videofilename)
                self.mouse_soft_pos = False  # reset jemného posuvu
                if self.editmode == True:
                    self.edl_cutter(round(self.api.position, 2))
                self.lcd_r['text'] = str(self.api.position) + ' s z' +\
                    str(self.api.duration) + ' s'
                self.gprint(_('Accurate position: ') + str(self.api.position))
        else:
            self.gprint(_('First you need to open a video file!'))
            
    def edl_insert_new(self, e):
        position = self.api.position
        self.edl_cutter(position, type='new')

    def edl_cutter(self, position, type='edit'):
        '''Dle hodnoty position při posuvu překresluje i obdelník nového cutu
        při tvorbě, nebo editaci nového cutu před vložením do EDL. Funkce
        je volána klikem do zelene pro vytvoření nového cutu a dále se edituje
        posuvem modreho posuvniku'''
        if type == 'new':
            new_cut = [position, position]  # novy cut na pretoc. pozici
            cut_index = len(self.edl.edl)
            edit_to = []  # edit_to nezadano
        # úprava existujiciho nějaký cut je vybrán a edit mod je spuštěn
        elif self.edl.sel_cut_index != [None, None] and self.editmode == True:
            cut_index = self.edl.sel_cut_index[0]  # index_cut vybr. cutu
            mark_index = self.edl.sel_cut_index[1]  # index_mark vybr. marku
            new_cut = list(self.edl.edl[cut_index])  # editovany cut
            new_cut[mark_index] = position  # uprava mark_time vybraneho marku
            edit_to = [cut_index]  # index cutu v EDL jenz se edituje v []
            if new_cut[0] >= new_cut[1]:
                if mark_index == 1:  # prohodi start end pri pretazeni
                    self.cut_activate(cut_index, 0)  # konce
                else:
                    self.cut_activate(cut_index, 1)  # nebo zacatku
        try:
            self.edl.edl_build_validate(new_cut, self.edl.edl,
                self.api.duration, edit_to=edit_to)  # validace
            self.edl.edl_build(new_cut, self.edl.edl, self.api.duration,
                edit_to=edit_to)  # vložení upr kopie do EDL
            self.edl_render(self.edl.edl, method='redraw')
            self.lcd_l['text'] = _('Editing ') + str(cut_index + 1) +\
                _('. cut ') + str(self.edl.edl[cut_index])
            # auto označeni do edit modu a vybrani end marku pro posun
            if type == 'new':
                cut_index, mark_index = self.edl.find_pos_nearest_mark(
                    position, self.edl.edl, self.api.duration, direction='abs')
                self.cut_activate(cut_index, 1)  # aktivuj cut a levy mark
                self.edit_cut_changer()
        except Exception as er:
            self.gprint(er.args[1])

    def edit_cut_changer(self, e=''):
        '''Ovladač pro prepinani cut modů select pro ukázku a mazání a edit
        modu pro úpravu (resizing)'''
        if e and e.type == '4':  # kliknutím
            position = e.x * self.spid
        elif e and e.type == '2' and e.keysym == 'Shift_R' or not e:
            # nebo dle pozice se vybere nejblizsi cut/mark
            position = self.api.position
        # x sour. na cas a nejblizsi mark
        cut_index, mark_index = self.edl.find_pos_nearest_mark(
            position, self.edl.edl, self.api.duration)
        # není aktivovaný
        if self.edl.sel_cut_index == [None, None]:
            self.cut_activate(cut_index, mark_index)  # aktivace cut_marku
            self.lcd_l['bg'] = '#DDFFDE'  # zelene lcd
        # uz aktivovany - vstup do edit mode
        elif self.editmode is not True:
            self.gprint(
                _('Editing cut by position.') +
                _(' Ends with Esc, deleting Delete LM,') +
                _('Ctrl + <- -> next cut mark.'))
            self.editmode = True  # aktivace edit modu
            self.cut_blink()  # blikat
            self.lcd_l['bg'] = '#FBC3C5'  # cervene lcd
        elif self.editmode == True:
            self.editmode = False
            self.deselect_cut()
            self.lcd_l['bg'] = '#FFFCDD'  # zpet na vychozi barvu

    def cut_delete(self, e=''):
        '''Odstranění prave vybraneho cutu v select mode z EDL a prekresleni
        platna strihu'''
        if self.edl.edl and self.edl.sel_cut_index != [None, None]:
            if self.editmode == True:  # deletovat se bude v edit modu
                cut_index = self.edl.sel_cut_index[0]  # index selection cutu
                if e:
                    confirm = messagebox.askyesno(_('Deleting cut!'),
                        _('Really delete ') +
                        str(cut_index + 1) + _('. cut ?'))
                else:
                    confirm = True
                if confirm == True:
                    del(self.edl.edl[cut_index])  # vymaz
                    self.deselect_cut()  # deselect cut
                    self.edl_render(self.edl.edl, method='redraw')  # render
                    print('DEBUG EDL CHANGE to: ' + str(self.edl.edl))
                    self.gprint('Střih ' + str(cut_index) +
                        _(' was deleted from the EDL'))

    def cut_activate(self, cut_index, mark_index):
        '''aktivuje vybraný cut (zcervená) rusi vyber stareho
        pretoci na novou pozici vybraneho marku'''
        old_sel_cut_index = self.edl.sel_cut_index[0]
        if old_sel_cut_index != None:  # existuje starý výběr
            self.cutting.itemconfig(self.edl_cuts[old_sel_cut_index],
                fill='#AB0000')  # zrusit zcervenani
        position = self.edl.edl[cut_index][mark_index]  # nova pozice
        self.api.seek(position)  # přetočit na novou pozici
        self.api.position = position  # ulozit novou pozici
        self.edl.sel_cut_index = [cut_index, mark_index]  # novy sel. index
        self.pos_progress(position)  # posunout progressbar a zobrazit v lcd_l
        mark_text = _('Start ') if mark_index == 0 else _('End ')
        self.lcd_l['text'] = mark_text + str(cut_index + 1) + _('. cut ') +\
            str(self.edl.edl[cut_index])
        self.cutting.itemconfig(self.edl_cuts[cut_index], fill='red')  # select
        self.gprint(
            str(cut_index + 1) + _('. cut selected. ') +
            _(' Back Esc, next cut mark Ctrl + <- ->, editing R-Shift/LM'))

    def cut_blink(self):
        '''vizualni blikani editovaneho cutu pri editovani'''
        cut_index = self.edl.sel_cut_index[0]
        normal_colors = ['#AB0000', '#FFFCDD']  # cut, lcd_l
        glow_colors = ['red', '#FBC3C5']  # glow color for blink mode
        if self.editmode == True:  # blink only edit mode
            cut_item_color = self.cutting.itemcget(self.edl_cuts[cut_index],
                'fill')  # get actual color for cut
            lcd_item_color = self.lcd_l['bg']  # get actual color for lcd_l
            if cut_item_color == normal_colors[0]\
                and lcd_item_color == normal_colors[1]:
                self.cutting.itemconfig(self.edl_cuts[cut_index],
                    fill=glow_colors[0])
                self.lcd_l['bg'] = glow_colors[1]
            else:
                self.cutting.itemconfig(self.edl_cuts[cut_index],
                    fill=normal_colors[0])
                self.lcd_l['bg'] = normal_colors[1]
            self.blinkator = self.gui.after(self.blink_time, self.cut_blink)

    def deselect_cut(self, e=''):
        '''Resetuje vyběr editovaneho cutu při kliku do zelene oblasti
        nebo stisku kl. Esc'''
        cut_index, mark_index = self.edl.sel_cut_index
        if cut_index is not None:
            if self.editmode == True:
                self.gui.after_cancel(self.blinkator)  # zrusit blikani
            self.lcd_l['text'] = _('Not selected cut')
            self.cutting.itemconfig(self.edl_cuts[cut_index],
                fill='#AB0000')
            self.edl.sel_cut_index = [None, None]
            self.editmode = False
            self.lcd_l['bg'] = '#FFFCDD'  # zpet na vychozi barvu
            self.gprint(_('Selecting cut deactivated'))

    def edl_render(self, edl_list, method='resize'):
        '''překreslí interacktivní čtverce střihů (self.edl_cuts)
        při editaci, naimportování EDL souboru, nebo změně
         velikosti okna dle zadaných souřadnic a přidá do self.edl_cuts'''
        if method == 'redraw':
            for cut_rect in self.edl_cuts:  # smazani starych obdelniku
                self.cutting.delete(cut_rect)  # v platne strihu
            self.edl_cuts = []  # vynulovani seznamu ID cutů v gui
        for cut in edl_list:
            cutx_start, cutx_end = cut[0] / self.spid, \
                cut[1] / self.spid  # ziskej casy
            index_cut = edl_list.index(cut)  # index strihu v self.edl.edl
            if method == 'redraw':  # kompletni překresleni střihu odznova
                self.edl_cuts.append(self.cutting.create_rectangle(
                    cutx_start, 0, cutx_end, 22, fill='#AB0000', width=0))
            # jen změny velikostí cutu při změně vel. okna
            elif method == 'resize':
                self.cutting.coords(
                    self.edl_cuts[index_cut], cutx_start, 0, cutx_end, 22)
            self.edl.sorter(edl_list)  # serareni

    def gprint(self, message):
        self.info['text'] = message
        print('GUI>>' + str(message))

    def sec_to_pix_ratio(self, duration_time):
        '''Vrátí koeficient poměr seconds/pixels při zadané časové délce
        delka celeho videa'''
        return duration_time / self.pbar.winfo_width()  # vynucená délka

    def rewinder(self, direction):
        '''Přetáčení vpřed nebo vzad'''
        if self.api.duration:
            if direction == 'back':
                position = self.api.position - self.shift_actual_value
            elif direction == 'forw':
                position = self.api.position + self.shift_actual_value
            self.api.seek(position)
            self.pos_progress(position)
            try:
                self.api.position = self.api.get_position()
            except Exception as er:
                self.gprint(er.args[1])
                self.open_video(filename=self.api.videofilename)
            if self.editmode == True:
                try:
                    self.edl_cutter(round(position, 2))
                except Exception as er:
                    self.gprint(er)
            else:
                self.gprint(_('Accurate position: ') + str(self.api.position))
        else:
            self.gprint(_('You do not have any open video!'))

    def mark_rewinder(self, direction):
        '''Přetočí na předchozi, nebo dalsi cutmark od toho nejblizsiho,
         ktery najde edl.find_pos_nearest_mark'''
        if self.edl.edl:
            # pozice nejb. marku
            cut_index, mark_index = self.edl.find_pos_nearest_mark(
                self.api.position, self.edl.edl, self.api.duration,
                    direction=direction)
            self.cut_activate(cut_index, mark_index)
        else:
            self.gprint('EDL cuts list is empty!')

    def pos_progress(self, time):
        '''Překresluje progressbar videa (velikost obdélníku) v plátně střihu
        na časovou hodnotu v time - absolutně zadanou'''
        self.pbar.update_idletasks()
        if self.api.duration:  # video je otevřeno a délka je známá
            self.lcd_r['text'] = str(round(self.api.position, 2)) + ' s z ' +\
            str(self.api.duration) + ' s'
            pixels = time / self.spid
            self.pbar.coords(self.progress, 0, 0, pixels, 16)

    def redraw_canvas(self, e=''):
        '''Přepočítat a překreslit prvky v kanvasech a jeho prvky při změně
        velikosti okna aplikace ve správném poměru velikostí'''
        self.pbar.update_idletasks()
        # spid a spis seconds/pixels pro duration seconds/pixels pro shift
        self.spid = self.sec_to_pix_ratio(self.api.duration)  # sec/pix delku
        self.spis = self.sec_to_pix_ratio(self.shift_actual_value)  # // shift
        self.pos_progress(self.api.position)  # překr progressbaru
        self.edl_render(self.edl.edl, method='resize')
        self.gprint(_('Rewind ') + str(self.spid) +
                ' sec/pix - ' + _('soft ') + str(self.spis) + ' sec/pix')

    def actual_position(self):
        '''Pravidelné zjišťování pozice každou sekundu'''
        paused = self.api.command('is_paused')
        if paused == 'no':
            try:
                self.api.position = self.api.get_position()
                self.pos_progress(self.api.position)
                # pred koncem videa zastav aby neskoncilo
                if self.api.position > self.api.duration - (
                    self.api.safe_end_time * 2):
                    self.api.seek(self.api.duration)  # skok na konec
            except Exception as er:
                self.gprint(er.args[1])
                self.open_video(filename=self.api.videofilename)
        self.timer = self.gui.after(100, self.actual_position)