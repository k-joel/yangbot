# author: github.com/k-joel

import json
import requests
import logging
import html
from bs4 import BeautifulSoup
from unidecode import unidecode

from markdown import MarkdownConverter

URL_PREFIX = 'https://www.yangforny.com'
URL_POLICY = 'https://www.yangforny.com/policies/'

POLICY_KEYWORDS = {
    'A Basic Income for New York City': [
        'ubi', 'universal basic income', 'minimum income', 'guaranteed income', 'freedom dividend'],
}

POLICIES_FILE = 'policies_yangforny.json'

POLICIES = None

LOGGER = logging.getLogger()


class PolicyMetadata:
    def __init__(self, title, url, categories):
        self.title = title
        self.url = url
        self.categories = categories


def get_policies_metadata():
    response = requests.get(URL_POLICY)
    soup = BeautifulSoup(response.content, 'lxml')

    filtered_links = [link for link in soup.findAll('a') if
                      link.get('href')[:10] == '/policies/']

    metadata = []
    for link in filtered_links:
        title = link.find(['h3', 'h4'])
        if not title:
            continue
        url = link.get('href')
        catgs = link.find('p').text.split(' | ')
        metadata.append(PolicyMetadata(title.text, url, catgs))

    return metadata


def scrape_policy(title, url, categories):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')
    conv = MarkdownConverter(URL_PREFIX)

    contents = soup.find('section', class_='wrapper').contents[1:]

    sections = []
    for section in contents:
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
            title = pm.title
            url = URL_PREFIX + pm.url
            category = pm.categories
            policy = scrape_policy(title, url, category)
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
        full_text += '# ' + policy['title'] + '\n\n'
        for text in policy['sections']:
            full_text += text
            full_text += '\n\n'
    full_text += '------\n\n'

    with open('dump_yangforny.md', 'w') as file:
        file.write(full_text)
