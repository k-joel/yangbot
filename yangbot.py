# author: github.com/k-joel

import praw
import prawcore
import sys
import logging
import time
from fuzzywuzzy import process
from unidecode import unidecode

import policies_yang2020
import policies_yangforny

ACTIVE_SUBREDDITS = [
    'YangForPresidentHQ',
    'YangGang',
    'yangformayorhq',
    'testingground4bots'
]

FOOTER = "^Beep ^Boop! ^I'm ^a ^bot! ^Bugs? ^Feedback? "\
    "^Contact ^my ^[author](https://www.reddit.com/message/compose?to=k_joel&subject=[yangbot]) "\
    "^or ^join ^the ^[discussion](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/). "\
    "^The ^[source](https://github.com/k-joel/yangbot)."

SHORT_ERROR = "Sorry, I was unable to process your query. The query length should be atleast 3 characters or more. Please try again."

MATCH_ERROR = "Sorry, I couldn't find a match for your query \'%s\'.\n\n"\
    "If you think this is an error or you wish to add this phrase to the related keyword list,"\
    " please comment [here](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/)"

COMMAND = '!yangbot'
COMMAND2020 = '!yangbot-2020'
MIN_PHRASE_LEN = 2
CHARACTER_LIMIT = 9000

TEST_FILE = 'test.md'
LOG_FILE = 'log.txt'
LOG_FORMAT = '[%(asctime)s] %(levelname)-8s %(message)s'

LOGGER = None


def config_logger():
    global LOGGER
    if LOGGER:
        return

    LOGGER = logging.getLogger()
    LOGGER.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    LOGGER.addHandler(console_handler)
    LOGGER.addHandler(file_handler)


def config_dev_logger():
    global LOGGER
    if LOGGER:
        return

    LOGGER = logging.getLogger()
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
        if process.extractOne(phrase, aliases, score_cutoff=85):
            LOGGER.info('Resolved keyword \'%s\' to \'%s\'' % (phrase, key))
            return key
    return phrase


def match_policy(phrase, policies, keywords):

    def get_title(d):
        return d['title'] if isinstance(d, dict) else d

    phrase = resolve_keywords(phrase, keywords)

    match = process.extractOne(
        phrase, policies, processor=get_title, score_cutoff=95)
    if not match:
        return None

    return match[0]


def build_policy(policy):
    texts = []
    full_text = '# ' + policy['title'] + '\n\n'

    length = 0
    for text in policy['sections']:
        if length + len(text) > CHARACTER_LIMIT:
            texts.append(full_text)
            full_text = ''
            length = 0
        length += len(text)
        full_text += text + '\n\n'

    full_text += '[**More info...**](' + policy['url'] + ')'
    full_text += '\n\n------\n\n' + FOOTER

    texts.append(full_text)
    return texts


def dev_main(phrase):
    config_dev_logger()

    if len(phrase) < MIN_PHRASE_LEN:
        return

    policies_pair = policies_yangforny.get_policies_and_keywords()
    if not policies_pair:
        return

    policy = match_policy(phrase, policies_pair[0], policies_pair[1])
    if not policy:
        return

    texts = build_policy(policy)
    text = ''
    if len(texts) == 1:
        text = texts[0]
    else:
        for i, text in enumerate(texts):
            text += 'Part [%s / %s]\n\n%s' % (
                str(i+1), str(len(texts)), text)

    print(text)
    # dump_text_to_file(text)


def main():
    config_logger()

    LOGGER.info('--- Yangbot started ---')

    new_policies_pair = policies_yangforny.get_policies_and_keywords()
    old_policies_pair = policies_yang2020.get_policies_and_keywords()
    if not new_policies_pair or not old_policies_pair:
        return

    lookup = {
        COMMAND: new_policies_pair,
        COMMAND2020: old_policies_pair
    }

    # init using praw.ini
    reddit = praw.Reddit("yangbot", config_interpolation="basic")

    bot_profile = reddit.redditor('yangpolicyinfo_bot')
    subreddit_string = bot_profile.subreddit['display_name'] +\
        '+' + '+'.join(ACTIVE_SUBREDDITS)

    subreddits = reddit.subreddit(subreddit_string)

    LOGGER.info('Polling /r/' + subreddit_string)

    for comment in subreddits.stream.comments(pause_after=10, skip_existing=True):
        if comment == None or comment.author == reddit.user.me():
            continue

        if len(comment.body) < len(COMMAND) or\
                comment.body[0] != '!':
            continue

        command_query = comment.body.split(' ', 1)

        if command_query[0] not in lookup:
            continue

        if len(command_query) < 2 or len(command_query[1]) < MIN_PHRASE_LEN:
            comment.author.message('Yangbot Error!', SHORT_ERROR)
            continue

        command = command_query[0]
        phrase = unidecode(command_query[1].splitlines()[0].strip().lower())

        LOGGER.info(
            'Querying \'%s %s\' by \'u/%s\' from \'r/%s\'' % (
                command, phrase, str(comment.author), str(comment.subreddit)))

        try:
            policies, keywords = lookup[command]
            policy = match_policy(phrase, policies, keywords)

            if policy:
                texts = build_policy(policy)
                if len(texts) == 1:
                    reply = comment.reply(texts[0])
                    LOGGER.info('Success! Reply: reddit.com' +
                                str(reply.permalink))
                else:
                    LOGGER.info('Sending multipart reply...')
                    for i, text in enumerate(texts):
                        text_part = 'Part [%s / %s]\n\n%s' % (
                            str(i+1), str(len(texts)), text)
                        reply = comment.reply(text_part)
                        LOGGER.info('Success! Reply %s: reddit.com%s' %
                                    (str(i), str(reply.permalink)))
                        # slow down otherwise the comment gets removed
                        time.sleep(5)

            else:
                comment.author.message('Yangbot Error!', MATCH_ERROR % phrase)
                LOGGER.info('Failed match!')

        except Exception as e:
            LOGGER.critical('!!Exception raised!!\n' + str(e))


def main_rs():
    while True:
        try:
            main()
        except prawcore.exceptions.ServerError:
            LOGGER.critical('!!503 Error!! Restarting in 10 seconds...')
            time.sleep(10)
        except:
            break


if __name__ == "__main__":
    dev_main('sanctuary city')
    # main_rs()
