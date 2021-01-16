# author: github.com/k-joel

import praw
import sys
import logging
from fuzzywuzzy import process

import policies_yang2020
import policies_yangforny

FOOTER = "^Beep ^Boop! ^I'm ^a ^bot! ^Bugs? ^Feedback? "\
    "^Contact ^my ^[author](https://www.reddit.com/message/compose?to=k_joel&subject=[yangbot]) "\
    "^or ^join ^the ^[discussion](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/). "\
    "^The ^[source](https://github.com/k-joel/yangbot)."

MATCH_ERROR = "Sorry! No match found for query \'%s\'.\n\n"\
    "If you think this is an error or you wish to add this to the keyphrase list,"\
    " please comment [here](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/)"

ACTIVE_SUBREDDITS = [
    'YangForPresidentHQ',
    'YangGang',
    # 'yangformayorhq',
    'testingground4bots'
]


COMMAND = '!yangbot'
COMMAND2020 = '!yangbot-2020'
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


def resolve_keywords(phrase, keywords):
    for key, aliases in keywords.items():
        if process.extractOne(phrase, aliases, score_cutoff=97):
            LOGGER.info('resolved keyword \'%s\' to \'%s\'' % (phrase, key))
            return key
    return phrase


def match_policy(policies, phrase, keywords):
    if len(phrase) < MIN_PHRASE_LEN:
        LOGGER.error('Phrase too short')
        return None

    phrase = resolve_keywords(phrase, keywords)

    def get_title(d):
        return d['title'] if isinstance(d, dict) else d

    match = process.extractOne(
        phrase, policies, processor=get_title, score_cutoff=90)
    if not match:
        LOGGER.error('No match found')
        return None

    return match[0]


def build_policy(policy):
    full_text = '# ' + policy['title'] + '\n\n'

    for text in policy['sections']:
        full_text += text
        full_text += '\n\n'

    full_text += '[**More info...**](' + policy['url'] + ')'

    full_text += '\n\n------\n\n' + FOOTER

    return full_text


def dev_main(phrase):
    config_dev_logger()

    policies = policies_yangforny.get_policies()
    if policies:
        policy = match_policy(
            policies, phrase, policies_yangforny.POLICY_KEYWORDS)
        if policy:
            text = build_policy(policy)
            print(text)
            # dump_text_to_file(text)


def main():
    config_logger()

    LOGGER.info('--- Yangbot started ---')

    policies_new = policies_yangforny.get_policies()
    policies_old = policies_yang2020.get_policies()
    if not policies_new or not policies_old:
        return

    lookup = {
        COMMAND: (policies_new, policies_yangforny.POLICY_KEYWORDS),
        COMMAND2020: (policies_old, policies_yang2020.POLICY_KEYWORDS)
    }

    # init using praw.ini
    reddit = praw.Reddit("yangbot", config_interpolation="basic")

    bot_profile = reddit.redditor('yangpolicyinfo_bot')
    subreddit_string = bot_profile.subreddit['display_name'] +\
        '+' + '+'.join(ACTIVE_SUBREDDITS)

    subreddits = reddit.subreddit(subreddit_string)

    for comment in subreddits.stream.comments(pause_after=10, skip_existing=True):
        if comment == None or comment.author == reddit.user.me():
            continue

        if len(comment.body) < len(COMMAND) + 1 or\
                comment.body[0] != '!':
            continue

        command, text = comment.body.split(' ', 1)

        if command not in lookup:
            continue

        phrase = text.splitlines()[0].strip().lower()

        LOGGER.warning(
            'Querying \'%s %s\' by \'u/%s\' from \'r/%s\'' % (
                command, phrase, str(comment.author), str(comment.subreddit)))

        try:
            policies, keywords = lookup[command]
            policy = match_policy(policies, phrase, keywords)

            if policy:
                text = build_policy(policy)
                botreply = comment.reply(text)
                if botreply:
                    LOGGER.info('Success! reply: reddit.com' +
                                str(botreply.permalink))
            else:
                botreply = comment.reply(MATCH_ERROR % phrase)
                if botreply:
                    LOGGER.info('Match failed! reply: reddit.com' +
                                str(botreply.permalink))

        except Exception as e:
            LOGGER.critical('!!Exception raised!!\n' + str(e))


if __name__ == "__main__":
    # dev_main('basic income')
    main()
