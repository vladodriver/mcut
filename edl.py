import os


class Edl:
    '''Třída vytváření, import, validaci a ukládání EDL'''

    def __init__(self):
        self.new_cut = [None, None]  # novy cut pred vlozenim EDL pro validaci
        self.edl = []   # aktuálně zpracovávané EDL při střihu
        self.sel_cut_index = [None, None]  # index vybraného [cut, mark] (red)
        self.imported_edl = []  # edl pro import ze souboru
        self.edlname = ''  # cesta k aktuálně otevřenému souboru EDL

    def edl_name(self, videofilename):
        '''Dle nazvu otevřeneho videa vytvoři nazev EDL'''
        if os.path.exists(videofilename):
            self.edlname = os.path.splitext(videofilename)[0] + '.edl'
        return True

    def find_pos_nearest_mark(self, mark_time, edl_list, duration,
        direction='abs'):
        '''Najde nejbližší další cutmark k aktuální pozici v edl_list
        a vrátí jeho index v edl_list, nejbl. mensi (dir='back')
        vetsi (dir='next') nebo absolutní hodnota (dir='abs')'''
        if edl_list:
            mark_list = []  # prevest edl_list na mark_list do rady za sebou
            [(mark_list.append(cut[0]),
                mark_list.append(cut[1])) for cut in edl_list]
            distance = duration
            # absolutní pozice
            for mark in mark_list:
                dist_now = abs(mark_time - mark)
                if distance > dist_now:
                    distance = dist_now
                    index = mark_list.index(mark)
                    position = mark_list[index]
            # posouvani pro dir='back' nebo 'next' - plati abs nebo:
            if direction == 'back':
                # 1. mark je doraz - kdyz nejsme na prvnim marku muzeme -1
                if index > 0 and mark_time <= position:  # 1. mark je doraz
                    index = index - 1  # muzeme + 1 dolů
                    position = mark_list[index]
                    print(_('DEBUG Correction backward'))
            elif direction == 'next':
                # kdyz nejsme na poslednim indexu muzeme pridat + 1
                if index < len(mark_list) - 1 and position <= mark_time:
                    index = index + 1
                    position = mark_list[index]
                    print('DEBUG Correction forward')
            for cut in edl_list:
                for mark in cut:
                    if mark == position:
                        index = [edl_list.index(cut), cut.index(mark)]
                        return index
        else:
            raise Exception('ValueError',
                _('EDL cuts list is empty'))

    def edl_build_validate(self, new_cut, edl_list, duration, edit_to=[]):
        '''Validace start/end nového nebo editovaného cutu type "new" pro nový
        a "resize" pro editovaný. Nesmi byt mimo video, zaplnit cele video,
        zasahnout do existujiciho strihu nebo jej pohltit'''
        for mark_time in new_cut:  # validace start/end i kdyz je prazdny EDL
            # není mimo video ?
            if mark_time < 0 or mark_time > duration:
                raise Exception('ValueError',
                    _('Marked point ') + str(mark_time) +
                        _(' is outside the timeline video!'))
            # cut je přes celé video
        if new_cut[0] == 0 and new_cut[1] == duration:
                raise Exception('ValueError',
                    _('This cut would take up the whole video, ') +
                    _(' and it does not make sense!'))
        if edl_list:  # neco uz je v EDL
            if edit_to:  # zjistuje se jen kdyz je zadan edit_to index editace
                # není již v "red area" ? vyjme se editovany z validace na ra
                edl_validate_list = list(edl_list)
                try:
                    del(edl_validate_list[edit_to[0]])
                except:
                    raise Exception('IndexError:',
                        _('Cut index: ') + str(edit_to[0]) + _(' not exists!'))
            else:
                edl_validate_list = list(edl_list)
            for cut in edl_validate_list:
                for mark in new_cut:
                    if cut[0] <= mark and cut[1] >= mark:
                        raise Exception('ValueError',
                            _('Cut point ') + str(mark_time) +
                            _(' is part of the ') + str(edl_list.index(cut)) +
                            _('. cut ') + str(cut) + ' !')
                if new_cut[0] < cut[0] < cut[1] < new_cut[1]:
                    raise Exception('ValueError',
                        _('New cut would absorb area of ') +
                        str(edl_list.index(cut) + 1) +
                        _('. cut ') + str(cut) + ' !')
        return True

    def edl_build(self, new_cut, edl_list, duration, edit_to=[]):
        '''Po validaci edl_build validate edituje nebi vlkládá záznam do EDL.
        Cuty se pak vysortují. Edit_to je index vutu v EDL ktery se
        ma editovat'''
        if not edit_to:
            self.edl_build_validate(new_cut, edl_list, duration)
            print('DEBUG CUT: ' + str(new_cut) + _(' > inserting new cut'))
        elif edit_to:
            self.edl_build_validate(new_cut, edl_list, duration,
                edit_to=edit_to)
            print('DEBUG CUT: ' + str(new_cut) + _(' > editing '))

        if not edit_to:
            edl_list.append(new_cut)
            edl_list.sort()  # seradit EDL
        elif edit_to:
            edl_list[edit_to[0]] = new_cut
        print(_('DEBUG EDL CHANGE to: ') + str(edl_list))

    def validate_edl_line(self, line_text):
        '''Validace formátu jednoho řádku EDL souboru Mplayer EDL v. 1 před
        importem do aplikace'''
        line = line_text.split()
        # kontroly
        for val in line:
            try:
                float(val)
            except ValueError:
                raise Exception('ValueError',
                    _('String ') + val +
                    _(' can not be converted to a decimal number'))
        if len(line) != 3:
            raise Exception('ValueError',
                _('Line EDL file does not have the correct number of parts!'))
        elif line[2] != '0':
            raise Exception('ValueError',
                _('Line EDL file does not end with 0!'))
        return True

    def sorter(self, edl_list):
        '''seřadi marky v cutech a cuty v EDL'''
        for cut in edl_list:
            cut.sort()
        edl_list.sort()

    def import_edl(self, edl_path, duration):
        '''Importuje existují EDL soubor z edl_path
         do EDL listu self.imported_edl odtud pak může být
         zkopírován do self.edl nebo porovnán s ním, jestli
         provedla aplikace změny ve svém EDL listu self.edl'''
        edl_file = open(edl_path, mode='r')
        edl_lines = edl_file.readlines()
        edl_file.close()
        for line in edl_lines:
            cut = [float(line.split()[0]), float(line.split()[1])]
            if self.edl_build_validate(cut, self.imported_edl, duration):
                self.edl_build(cut, self.imported_edl, duration)
        return True

    # uložení EDL do souboru
    def save_edl(self, file_path):
        '''Uložení do edl souboru self.edlname'''
        edl_text = ''
        with open(file_path, mode='w') as edl_file:
            for cut in self.edl:
                edl_text += str(cut[0]) + ' ' + str(cut[1]) + ' ' + '0\n'
            edl_file.write(edl_text)
        return True
