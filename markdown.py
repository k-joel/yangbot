import unicodedata
from common import URL_PREFIX
from bs4 import NavigableString, Tag

IGNORED_CLASSES = ['check', 'material-icons']


def add_line(index, n=1):
    return '\n' * n if index > 0 else ''


def strip_and_enclose(string, es):
    s = ' ' if string[0] == ' ' else ''
    s += es + string.strip() + es
    if string[-1] == ' ':
        s += ' '
    return s


def format_contents(section, is_ord=False):
    s, i = '', 0
    for child in section.children:
        f = format_section(child, i, is_ord)
        if f != '' and not f.isspace():
            s += f
            i += 1
    return s


def format_section_tag(section, index, is_ord, text):
    if text == '':
        return ''
    if section.name == 'b' or section.name == 'strong':
        return strip_and_enclose(text, '**')
    if section.name == 'i' or section.name == 'em':
        return strip_and_enclose(text, '*')
    if section.name == 'code':
        return strip_and_enclose(text, '`')
    if section.name == 'br':
        return add_line(index)
    if section.name == 'a':
        href = section['href']
        return '[' + text.strip() + '](' + URL_PREFIX + href.strip().replace(' ', '%20') + ')'
    if section.name == 'li':
        s = add_line(index, 2)
        s += str(index) + '.' if is_ord else '-'
        return s + ' ' + text.strip()
    if section.name == 'ol' or section.name == 'ul' or section.name == 'div' or section.name == 'p':
        return add_line(index, 2) + text
    if section.name[0] == 'h' and len(section.name) == 2:
        n = int(section.name[1])
        if n >= 1 and n <= 6:
            return add_line(index, 2) + ('#' * n) + ' ' + text.strip() + '\n------'
    return ''


def format_section(section, index=0, is_ord=False):

    if isinstance(section, NavigableString):
        if section.string != '\n':
            norm_string = unicodedata.normalize("NFKD", section.string)
            return norm_string
        return ''

    if isinstance(section, Tag):
        if 'class' in section.attrs and \
                any(x in IGNORED_CLASSES for x in section.attrs['class']):
            return ''

        if section.name == 'ol':
            is_ord = True
        inner_text = format_contents(section, is_ord)
        return format_section_tag(section, index, is_ord, inner_text)
