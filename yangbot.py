# author: github.com/k-joel

import praw
import sys
import os
import json
import logging
from fuzzywuzzy import process
from build_policies import get_policies

URL_PREFIX = 'https://www.yang2020.com'

FOOTER = "^Beep ^Boop! ^I'm ^a ^bot! ^Bugs? ^Feedback? " +\
    "^Contact ^my ^[author](https://www.reddit.com/message/compose?to=k_joel&subject=[yangbot]) " +\
    "^or ^join ^the ^[discussion](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/). " +\
    "^The ^[source](https://github.com/k-joel/yangbot)."

ACTIVE_SUBREDDITS = [
    'YangForPresidentHQ',
    'YangGang',
    # 'yangformayorhq',
    'testingground4bots'
]

POLICY_ALIASES = {
    'The Freedom Dividend': ['ubi', 'basic income', 'universal basic income'],
    'Value-Added Tax': ['vat']
}

COMMAND = '!yangbot'
MIN_PHRASE_LEN = 3

TEST_FILE = 'test.md'
LOG_FILE = 'log.txt'
LOG_FORMAT = '[%(asctime)s] %(levelname)-8s %(message)s'

LOGGER = logging.getLogger()


def config_logger():
    LOGGER.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    LOGGER.addHandler(console_handler)
    LOGGER.addHandler(file_handler)


def config_dev_logger():
    LOGGER.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    LOGGER.addHandler(console_handler)


def dump_text_to_file(text):
    with open(TEST_FILE, 'w') as file:
        file.write(text)


def resolve_aliases(phrase):
    for key, aliases in POLICY_ALIASES.items():
        if process.extractOne(phrase, aliases, score_cutoff=97):
            LOGGER.info('resolved alias \'{}\' to \'{}\''.format(phrase, key))
            return key
    return phrase


def find_and_build_policy(policies, phrase):
    if len(phrase) < MIN_PHRASE_LEN:
        LOGGER.error('phrase too short')
        return

    phrase = resolve_aliases(phrase)

    def get_title(d):
        return d['title'] if isinstance(d, dict) else d

    match = process.extractOne(
        phrase, policies, processor=get_title, score_cutoff=90)
    if not match:
        LOGGER.error('no match found')
        return

    title = match[0]['title']
    sections = match[0]['sections']

    full_text = '## ' + title + '\n\n------\n\n'

    for text in sections.values():
        full_text += text
        full_text += '\n\n'

    full_text += '[**More info...**](' + URL_PREFIX + match[0]['url'] + ')\n\n'

    # Footer
    full_text += '------\n\n' + FOOTER

    return full_text


def dev_main(phrase):
    config_dev_logger()

    policies = get_policies()
    if policies:
        policy = find_and_build_policy(policies, phrase)
        if policy:
            print(policy)
            # dump_text_to_file(policy)


def main():
    config_logger()

    LOGGER.info('--- yangbot started ---')

    policies = get_policies()
    if not policies:
        return

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
            'querying phrase \'{}\' by \'u/{}\' from \'r/{}\''.format(
                phrase, str(comment.author), str(comment.subreddit)))

        try:
            policy = find_and_build_policy(policies, phrase)
            if policy:
                botreply = comment.reply(policy)
                if botreply:
                    LOGGER.info('success! reddit.com' +
                                str(botreply.permalink))

        except Exception as e:
            LOGGER.critical('!!exception raised!!\n' + str(e))


if __name__ == "__main__":
    dev_main('nuclear energy')
    # main()
