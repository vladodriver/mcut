import locale
import gettext
import sys
import os

class Translate:
    '''Localization messages to non-english languages'''
    
    def __init__(self):
        # conversion table for unix and win locale names
        # http://msdn.microsoft.com/en-us/library/cdax410z%28VS.71%29.aspx
        # http://www.gnu.org/software/gettext/manual/html_node/
        # Usual-Language-Codes.html#Usual-Language-Codes
        # for translating add locale to this dict ex: 'ru': ['rus', 'russia']
        # and create mo file in locales directory
        self.locales = {
            'cs': ['cze', 'czech']
            }
        self.get_translations()
        
    def unix_to_win(self, locale_str):
        '''Convert unix locale string ex. cs to windows locale string
        ex. czech or csy'''
        unix_locale = ''
        for locale in self.locales:
            for lang in locale:
                if lang == locale_str:
                    unix_locale = locale
        if unix_locale:
            return unix_locale
        else:
            return False
        
    def get_translations(self):
        '''get path to mo file for translating messages and initiate it'''
        lang = locale.getlocale()[0]
        if sys.platform == 'linux' or sys.platform == 'darwin':  #lin & mac
            if lang:
                print(lang)
                locale_string = '{}.mo'.format(lang[0:2])
            else:
                locale_string = ''
        elif sys.platform == 'win32':  # win32
            if lang:
                locale_string = self.unix_to_win(lang)
            else:
                locale_string = ''
        locale_path = os.path.join('locales', locale_string)
        if locale_string and os.path.exists(locale_path):
            locale_path = os.path.join('locales', locale_string)
            print('DEBUG Translations for ' + str(lang) +
                ' locale will be loaded')
            trans = gettext.GNUTranslations(open( locale_path, "rb" ))
        else:
            print('DEBUG Translations files for ' + str(lang) +
                ' language not found! Use default messages!')
            trans = gettext.NullTranslations()
        trans.install()