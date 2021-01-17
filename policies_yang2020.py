# author: github.com/k-joel

import json
import requests
import logging
import html
from bs4 import BeautifulSoup
from unidecode import unidecode

from markdown import MarkdownConverter

URL_PREFIX = 'https://www.yang2020.com'
URL_POLICY = 'https://www.yang2020.com/policies/?tab=all'

POLICY_KEYWORDS = {
    'The Freedom Dividend': ['ubi', 'basic income', 'universal basic income'],
    'Value-Added Tax': ['vat']
}

SECTIONS = [
    'policy-individual-brief',
    'policy-problem',
    'policy-individual-goals',
    'policy-individual-president',
]

FILTERED_TAGS = {'class': 'check'}

POLICIES_FILE = 'policies_yang2020.json'

POLICIES = None

LOGGER = logging.getLogger()


def get_policies_metadata():
    response = requests.get(URL_POLICY)
    soup = BeautifulSoup(response.content, 'lxml')
    policies_section = soup.find_all(
        'section', class_='policy-list-section')[0]
    policies_text = unidecode(html.unescape(policies_section['data-policies']))
    policies_json = json.loads(policies_text)
    return policies_json


def scrape_policy(title, url, categories):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')
    conv = MarkdownConverter(URL_PREFIX, [], FILTERED_TAGS)

    sections = []
    for cls_ in SECTIONS:
        section = soup.find('div', class_=cls_)
        text = conv.format(section)
        sections.append(text)

    jsmap = {
        'title': title,
        'url': url,
        'categories': categories,
        'sections': sections,
    }

    return jsmap


def load_policies():
    try:
        with open(POLICIES_FILE, 'r') as json_file:
            LOGGER.info('Loading policies from file: ' + POLICIES_FILE)
            return json.load(json_file)
    except:
        pass
    try:
        LOGGER.info(
            'No json cache found, grabbing policy data from: ' + URL_POLICY)

        policies_meta = get_policies_metadata()
        policies = []

        for pm in policies_meta:
            title = pm['title']
            url = URL_PREFIX + pm['url']
            categories = [x['title'] for x in pm['categories']]
            policy = scrape_policy(title, url, categories)
            policies.append(policy)

        LOGGER.info('Dumping policies to file: ' + POLICIES_FILE)
        with open(POLICIES_FILE, 'w') as json_file:
            json.dump(policies, json_file, indent=4)

        return policies
    except Exception as e:
        LOGGER.critical('!!Exception raised!!\n' + str(e))
        return None


def get_policies_and_keywords():
    global POLICIES
    if not POLICIES:
        POLICIES = load_policies()
        if not POLICIES:
            return None
    return (POLICIES, POLICY_KEYWORDS)


if __name__ == "__main__":
    logging.basicConfig()
    policies = load_policies()

    full_text = ''
    for policy in policies:
        full_text += '## ' + policy['title'] + '\n\n------\n\n'
        for text in policy['sections']:
            full_text += text
            full_text += '\n\n'
    full_text += '------\n\n'

    with open('dump_yang2020.md', 'w') as file:
        file.write(full_text)
