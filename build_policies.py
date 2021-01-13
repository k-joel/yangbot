# author: github.com/k-joel

import unicodedata
import json
import requests
import logging
import html
from bs4 import BeautifulSoup, NavigableString, Tag
from unidecode import unidecode

URL_PREFIX = 'https://www.yang2020.com'
URL_POLICY = 'https://www.yang2020.com/policies/?tab=all'

SECTIONS = [
    ('brief', 'policy-individual-brief'),
    ('problems', 'policy-problem'),
    ('goals', 'policy-individual-goals'),
    ('as_president', 'policy-individual-president'),
]

FILTERED_CLASSES = ['check', 'material-icons']
FILTERED_CHARS = ['', ' ', '\n', '\r', '\t', u'\xa0']

TAG_BOLD = ['b', 'strong']
TAG_ITALIC = ['i', 'em']
TAG_CODE = ['code']
TAG_BREAK = ['br']
TAG_LINK = ['a']
TAG_LIST_ITEM = ['li']
TAG_LIST = ['ul', 'ol']
TAG_PARAGRAPH = ['div', 'p']
TAG_HEADING = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

LOGGER = logging.getLogger()

POLICIES_FILE = 'policies.json'


def is_tag(tag, catg):
    return any(tag.name == x for x in catg)


def add_line(index):
    return '\n\n' if index > 0 else ''


def strip_and_enclose(string, es):
    s = ' ' if string[0] == ' ' else ''
    s += es + string.strip() + es
    if string[-1] == ' ':
        s += ' '
    return s


def format_link(link):
    ln = link.strip().replace(' ', '%20')
    if len(ln) < 4 or ln[:4] != 'http':
        return URL_PREFIX + ln
    return ln


def format_tag(tag, parent_tag, index, text):
    if text == '':
        return ''

    if is_tag(tag, TAG_BOLD):
        return strip_and_enclose(text, '**')

    if is_tag(tag, TAG_ITALIC):
        return strip_and_enclose(text, '*')

    if is_tag(tag, TAG_CODE):
        return strip_and_enclose(text, '`')

    if is_tag(tag, TAG_BREAK):
        return add_line(1)

    if is_tag(tag, TAG_LINK):
        return '[' + text.strip() + '](' + format_link(tag['href']) + ')'

    if is_tag(tag, TAG_LIST_ITEM):
        s = add_line(index)
        s += str(index+1) + \
            '.' if parent_tag and parent_tag.name == 'ol' else '-'
        return s + ' ' + text.strip()

    if is_tag(tag, TAG_LIST) or is_tag(tag, TAG_PARAGRAPH):
        return add_line(index) + text

    if is_tag(tag, TAG_HEADING):
        n = int(tag.name[1])
        return add_line(index) + ('#' * n) + ' ' + text.strip() + '\n------'

    # unknown tag, just return the text
    return text


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
        if all(x in FILTERED_CHARS for x in section.string):
            return ''

        text = unidecode(section.string)
        return text

    if isinstance(section, Tag):
        if 'class' in section.attrs and \
                any(x in FILTERED_CLASSES for x in section.attrs['class']):
            return ''

        text = format_tag_contents(section)
        return format_tag(section, parent_tag, index, text)


def get_policies_metadata():
    response = requests.get(URL_POLICY)
    soup = BeautifulSoup(response.content, 'lxml')
    policies_section = soup.find_all(
        'section', class_='policy-list-section')[0]
    policies_text = unidecode(html.unescape(policies_section['data-policies']))
    policies_json = json.loads(policies_text)
    return policies_json


def scrape_policy(title, url, category):
    full_url = URL_PREFIX + url
    response = requests.get(full_url)
    soup = BeautifulSoup(response.content, 'lxml')

    jsmap = dict()

    jsmap['title'] = title
    jsmap['url'] = url
    jsmap['category'] = category

    sections = {}
    for key, cls_ in SECTIONS:
        section = soup.find('div', class_=cls_)
        sections[key] = format_section(section)

    jsmap['sections'] = sections

    return jsmap


def get_policies():
    try:
        with open(POLICIES_FILE, 'r') as json_file:
            LOGGER.info('loading policies from file: ' + POLICIES_FILE)
            return json.load(json_file)
    except:
        pass
    try:
        LOGGER.info(
            'no json cache found, grabbing policy data from: ' + URL_POLICY)

        policies_meta = get_policies_metadata()
        policies = []

        for pm in policies_meta:
            title = pm['title']
            url = pm['url']
            category = pm['categories'][0]['title']
            policy = scrape_policy(title, url, category)
            policies.append(policy)

        LOGGER.info('dumping policies to file: ' + POLICIES_FILE)
        with open(POLICIES_FILE, 'w') as json_file:
            json.dump(policies, json_file, indent=4)

        return policies
    except Exception as e:
        LOGGER.critical('!!exception raised!!\n' + str(e))
        return None


'''
if __name__ == "__main__":
    policies_meta = get_policies_metadata()
    with open('policies_meta.json', 'w') as json_file:
        json.dump(policies_meta, json_file, indent=4)
'''
