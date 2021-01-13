import unicodedata
from common import URL_PREFIX
from bs4 import NavigableString, Tag

FILTERED_CLASSES = ['check', 'material-icons']


def add_line(index):
    return '\n\n' if index > 0 else ''


def strip_and_enclose(string, es):
    s = ' ' if string[0] == ' ' else ''
    s += es + string.strip() + es
    if string[-1] == ' ':
        s += ' '
    return s


def format_tag(tag, parent_tag, index, text):
    if text == '':
        return ''

    if tag.name == 'b' or tag.name == 'strong':
        return strip_and_enclose(text, '**')

    if tag.name == 'i' or tag.name == 'em':
        return strip_and_enclose(text, '*')

    if tag.name == 'code':
        return strip_and_enclose(text, '`')

    if tag.name == 'br':
        return add_line(1)

    if tag.name == 'a':
        href = tag['href']
        return '[' + text.strip() + '](' + URL_PREFIX + href.strip().replace(' ', '%20') + ')'

    if tag.name == 'li':
        s = add_line(index)
        s += str(index) + '.' if parent_tag and parent_tag.name == 'ol' else '-'
        return s + ' ' + text.strip()

    if tag.name == 'ol' or tag.name == 'ul' or tag.name == 'div' or tag.name == 'p':
        return add_line(index) + text

    if tag.name[0] == 'h' and len(tag.name) == 2:
        n = int(tag.name[1])
        if n >= 1 and n <= 6:
            return add_line(index) + ('#' * n) + ' ' + text.strip() + '\n------'

    return ''


def format_tag_contents(tag):
    s, i = '', 0
    for child in tag.children:
        f = format_section(child, tag, i)
        if f != '' and not f.isspace():
            s += f
            i += 1
    return s


def format_section(section, parent_tag=None, index=0):
    if isinstance(section, NavigableString):
        if section.string == '\n':
            return ''

        norm = unicodedata.normalize("NFKD", section.string)
        return norm

    if isinstance(section, Tag):
        if 'class' in section.attrs and \
                any(x in FILTERED_CLASSES for x in section.attrs['class']):
            return ''

        text = format_tag_contents(section)
        return format_tag(section, parent_tag, index, text)
