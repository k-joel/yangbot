
import html
from bs4 import BeautifulSoup, NavigableString, Tag
from unidecode import unidecode

TAG_BOLD = ['b', 'strong']
TAG_ITALIC = ['i', 'em']
TAG_CODE = ['code']
TAG_SUPER = ['sup']
TAG_QUOTE = ['blockquote']
TAG_BREAK = ['br']
TAG_LINE = ['hr']
TAG_LINK = ['a']
TAG_LIST_ITEM = ['li']
TAG_LIST = ['ul', 'ol']
TAG_PARAGRAPH = ['div', 'p']
TAG_HEADING = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

# u'\xa0'
FILTERED_SPACE = [' ', '\t']
FILTERED_EMPTY = ['', ' ', '\t', '\n', '\r']


def is_tag(tag, catg):
    return any(tag.name == x for x in catg)


def strip_enclose(string, es):
    s = ' ' if string[0] == ' ' else ''
    s += es + string.strip() + es
    if string[-1] == ' ':
        s += ' '
    return s


def strip_special(string):
    s = ' ' if string[0] == ' ' else ''
    s += string.strip()
    if string[-1] == ' ':
        s += ' '
    return s


class MarkdownConverter:
    '''
    Simple HTML to Markdown converter

    url_prefix: Prefix this url to any relative links

    tag_filter: dict() that allows you to filter tags based on attributes.\
                Can accept the value of the key,value pair as string or list of strings
                e.g. { 'class': ['ignore', 'this'] }
    '''

    def __init__(self, url_prefix='', tag_filter={}):
        self.url_prefix = url_prefix
        self.tag_filter = tag_filter
        self.indent_level = 0
        self.indent = 0

    def add_indent(self):
        return ' ' * self.indent

    def add_line1(self, index):
        s = '\n' if index > 0 else ''
        return s + self.add_indent()

    def add_line2(self, index):
        s = '\n\n' if index > 0 else ''
        return s + self.add_indent()

    def can_filter_tag(self, tag):
        for key, value in self.tag_filter.items():
            if key in tag.attrs:
                attr_values = tag.attrs[key]
                if (isinstance(value, list) and any(x in value for x in attr_values)) or\
                        value in attr_values:
                    return True
        return False

    def format_link(self, link):
        ln = link.strip().replace(' ', '%20')
        if len(ln) < 4 or ln[:4] != 'http':
            return self.url_prefix + ln
        return ln

    def format_tag_contents(self, tag):
        s, i = '', 0
        for child in tag.children:
            f = self.format_section(child, tag, i)
            if f != '' and not (f == ' ' and len(s) > 0 and s[-1] == ' '):
                s += f
                i += 1
        return s

    def format_tag(self, tag, parent_tag, index):
        if self.can_filter_tag(tag):
            return ''

        if is_tag(tag, TAG_BREAK):
            return '\n\n'

        if is_tag(tag, TAG_LINE):
            return '\n\n------\n\n'

        if is_tag(tag, TAG_LIST):
            old_indent = self.indent
            self.indent = self.indent_level * 4
            text = self.format_tag_contents(tag)
            self.indent = old_indent
            if text == '':
                return ''
            return self.add_line2(index) + text

        if is_tag(tag, TAG_LIST_ITEM):
            self.indent_level += 1
            text = self.format_tag_contents(tag)
            self.indent_level -= 1
            if text == '':
                return ''
            s = self.add_line1(index)
            s += str(index+1) + '.' \
                if parent_tag and parent_tag.name == 'ol' else '-'
            return s + ' ' + text

        text = self.format_tag_contents(tag)
        if text == '':  # skip if no nested text
            return ''

        if is_tag(tag, TAG_BOLD):
            return strip_enclose(text, '**')

        if is_tag(tag, TAG_ITALIC):
            return strip_enclose(text, '*')

        if is_tag(tag, TAG_CODE):
            return strip_enclose(text, '`')

        if is_tag(tag, TAG_SUPER):
            words = text.split(' ')
            return '^' + ' ^'.join(words)

        if is_tag(tag, TAG_QUOTE):
            return '> ' + text

        if is_tag(tag, TAG_LINK):
            return '[' + text + '](' +\
                self.format_link(tag['href']) + ')'

        if is_tag(tag, TAG_PARAGRAPH):
            sep = '\n' + self.add_indent()
            return self.add_line2(index) + sep.join(text.splitlines())

        if is_tag(tag, TAG_HEADING):
            n = int(tag.name[1])
            return self.add_line2(index) + ('#' * n) + ' ' + text

        # unknown tag, just return the text
        return text

    def format_section(self, section, parent_tag, index):
        if isinstance(section, NavigableString):
            text = unidecode(section.string)
            if all(x in FILTERED_SPACE for x in text):
                return ' '
            if all(x in FILTERED_EMPTY for x in text):
                return ''
            return strip_special(text)

        if isinstance(section, Tag):
            return self.format_tag(section, parent_tag, index)

    def format(self, section):
        return self.format_section(section, None, 0)
