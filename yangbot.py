# author: github.com/k-joel

import praw
import sys
import os
import requests
import json
from bs4 import BeautifulSoup
from fuzzywuzzy import process
from markdown import format_section

from common import URL_PREFIX, URL_POLICY


FOOTER = "^Beep ^Boop! ^I'm ^a ^bot! ^Please ^contact ^[*u/k_joel*](https://reddit.com/user/k_joel) ^with ^any ^issues ^or ^suggestions. ^[*Github*](https://github.com/k-joel/yangbot)"

ACTIVE_SUBREDDITS = [
    'YangForPresidentHQ',
    'YangGang',
    'yangformayorhq'
]

POLICY_ALIASES = {
    'The Freedom Dividend': ['ubi', 'basic income', 'universal basic income'],
    'Value-Added Tax': ['vat']
}

COMMAND = 'yangbot'
MIN_PHRASE_LEN = 3
DUMP_FILE = 'dump.json'
TEST_FILE = 'test.md'
LOG_FILE = 'log.txt'


def dump_json_to_file(json_text):
    print('dumping json to file:', DUMP_FILE)
    data = json.loads(json_text)
    with open(DUMP_FILE, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    return data


def load_json_from_file():
    data = None
    with open(DUMP_FILE, 'r') as json_file:
        print('loading json from file:', DUMP_FILE)
        data = json.load(json_file)
    return data


def get_policies():
    data = load_json_from_file()
    if not data:
        print('parsing url:', URL_POLICY)
        response = requests.get(URL_POLICY)
        soup = BeautifulSoup(response.content, 'lxml')
        policies_section = soup.find_all(
            'section', class_='policy-list-section')[0]
        policies_text = policies_section['data-policies']
        print('done!')
        data = dump_json_to_file(policies_text)
    return data


def dump_text_to_file(text):
    with open(TEST_FILE, 'w') as file:
        file.write(text)


def extract_data(url, title):
    print('scraping policy:', url)
    full_url = URL_PREFIX + url
    response = requests.get(full_url)
    soup = BeautifulSoup(response.content, 'lxml')

    # Brief
    full_text = '## ' + title + '\n\n------\n\n'
    brief_section = soup.find('div', class_='policy-individual-brief')
    full_text += format_section(brief_section)
    full_text += '\n\n'

    # Problems to be solved
    problems_section = soup.find('div', class_='policy-problem')
    full_text += format_section(problems_section)
    full_text += '\n\n'

    # Goals
    goals_section = soup.find('div', class_='policy-individual-goals')
    full_text += format_section(goals_section)
    full_text += '\n\n'

    # As President...
    aspres_section = soup.find('div', class_='policy-individual-president')
    full_text += format_section(aspres_section)
    full_text += '\n\n------\n\n'

    # Footer
    full_text += FOOTER

    return full_text


def resolve_aliases(phrase):
    for key, aliases in POLICY_ALIASES.items():
        if process.extractOne(phrase, aliases, score_cutoff=97):
            return key
    return phrase


def match_and_extract_data(phrase):
    if len(phrase) < MIN_PHRASE_LEN:
        print('phrase too short')
        return None

    phrase = resolve_aliases(phrase)
    print('parsing phrase:', phrase)

    policies = get_policies()
    titles = {policy['title']: policy['url'] for policy in policies}

    match = process.extractOne(phrase, titles, score_cutoff=90)
    if not match:
        print('no match found')
        return None

    text = extract_data(match[0], match[2])
    return text


def append_log(text):
    with open(LOG_FILE, 'w+') as file:
        file.write(text)


def dev_main(phrase):
    text = match_and_extract_data(phrase)
    if text:
        print(text)
        # dump_text_to_file(text)


def main():
    # init using praw.ini
    reddit = praw.Reddit("yangbot", config_interpolation="basic")

    bot_profile = reddit.redditor('yangpolicyinfo_bot')
    bot_subreddit = reddit.subreddit(bot_profile.subreddit['display_name'])

    for comment in bot_subreddit.stream.comments(pause_after=10, skip_existing=True):
        if comment == None or comment.author == reddit.user.me():
            continue

        init_len = len(COMMAND) + 2

        if len(comment.body) < init_len or\
                comment.body[:init_len].lower() != '!' + COMMAND + ' ':
            continue

        phrase = comment.body.splitlines()[0][init_len:].lower()

        try:
            text = match_and_extract_data(phrase)
            if not text:
                continue

            comment.reply(text)
        except:
            append_log('error scraping phrase: ' + phrase)


if __name__ == "__main__":
    # dev_main('ubi')
    main()
