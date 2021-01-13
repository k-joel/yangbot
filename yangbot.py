# author: github.com/k-joel

import praw
import sys
import os
import requests
import json
import logging
from bs4 import BeautifulSoup
from fuzzywuzzy import process
from markdown import format_section

from common import URL_PREFIX, URL_POLICY

LOGGER = logging.getLogger("yangbot")

FOOTER = "^Beep ^Boop! ^I'm ^a ^bot! ^Bugs? ^Feedback? " +\
    "^Contact ^my ^[author](https://www.reddit.com/message/compose?to=k_joel&subject=[yangbot]) " +\
    "^or ^join ^the ^[discussion](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/). " +\
    "^The ^[source](https://github.com/k-joel/yangbot)."

ACTIVE_SUBREDDITS = [
    # 'YangForPresidentHQ',
    # 'YangGang',
    # 'yangformayorhq',
    'testingground4bots'
]

POLICY_ALIASES = {
    'The Freedom Dividend': ['ubi', 'basic income', 'universal basic income'],
    'Value-Added Tax': ['vat']
}

COMMAND = '!yangbot'
MIN_PHRASE_LEN = 3

DUMP_FILE = 'policies.json'
TEST_FILE = 'test.md'
LOG_FILE = 'log.txt'
LOG_FORMAT = '[%(asctime)s] %(levelname)-8s %(message)s'


def config_logger():
    LOGGER.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    LOGGER.addHandler(console_handler)
    LOGGER.addHandler(file_handler)


def config_dev_logger():
    LOGGER.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    LOGGER.addHandler(console_handler)


def dump_json_to_file(json_text):
    LOGGER.info('dumping json to file: ' + DUMP_FILE)
    data = json.loads(json_text)
    with open(DUMP_FILE, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    return data


def load_json_from_file():
    data = None
    with open(DUMP_FILE, 'r') as json_file:
        LOGGER.info('loading json from file: ' + DUMP_FILE)
        data = json.load(json_file)
    return data


def get_policies():
    data = load_json_from_file()
    if not data:
        LOGGER.info(
            'no json cache found, grabbing policy data from: ' + URL_POLICY)
        response = requests.get(URL_POLICY)
        soup = BeautifulSoup(response.content, 'lxml')
        policies_section = soup.find_all(
            'section', class_='policy-list-section')[0]
        policies_text = policies_section['data-policies']
        data = dump_json_to_file(policies_text)
    return data


def dump_text_to_file(text):
    with open(TEST_FILE, 'w') as file:
        file.write(text)


def extract_data(url, title):
    LOGGER.info('scraping policy from: ' + url)
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
            LOGGER.info('resolved alias \'{}\' to \'{}\''.format(phrase, key))
            return key
    return phrase


def extract_titles():
    policies = get_policies()
    titles = {policy['title']: policy['url'] for policy in policies}
    return titles


def dev_main(phrase):
    config_dev_logger()

    titles = extract_titles()
    phrase = resolve_aliases(phrase)

    match = process.extractOne(phrase, titles, score_cutoff=90)
    if not match:
        LOGGER.error('no match found')
        return

    text = extract_data(match[0], match[2])
    if text:
        print(text)
        # dump_text_to_file(text)


def main():
    config_logger()

    LOGGER.info('--- yangbot started ---')

    titles = extract_titles()

    # init using praw.ini
    reddit = praw.Reddit("yangbot", config_interpolation="basic")

    bot_profile = reddit.redditor('yangpolicyinfo_bot')
    subreddit_string = bot_profile.subreddit['display_name'] +\
        '+' + '+'.join(ACTIVE_SUBREDDITS)

    subreddits = reddit.subreddit(subreddit_string)

    for comment in subreddits.stream.comments(pause_after=10, skip_existing=True):
        if comment == None or comment.author == reddit.user.me():
            continue

        init_len = len(COMMAND) + 1

        if len(comment.body) < init_len or\
                comment.body[:init_len].lower() != COMMAND + ' ':
            continue

        phrase = comment.body.splitlines()[0][init_len:].lower()

        LOGGER.warning(
            'querying phrase \'{}\' by user \'{}\' from subreddit \'{}\''.format(
                phrase, str(comment.author), str(comment.subreddit)))

        if len(phrase) < MIN_PHRASE_LEN:
            LOGGER.error('phrase too short')
            continue

        phrase = resolve_aliases(phrase)

        match = process.extractOne(phrase, titles, score_cutoff=90)
        if not match:
            LOGGER.error('no match found')
            continue

        try:
            text = extract_data(match[0], match[2])
            if text:
                botreply = comment.reply(text)
                if botreply:
                    LOGGER.info('success! permalink: reddit.com' +
                                str(botreply.permalink))

        except Exception as e:
            LOGGER.critical('!!exception raised!!\n' + str(e))


if __name__ == "__main__":
    dev_main('nuclear energy')
    # main()
