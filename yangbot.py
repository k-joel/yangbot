# author: github.com/k-joel

import praw
import prawcore
import time
from fuzzywuzzy import process
from unidecode import unidecode

import policies_yang2020
import policies_yang4nyc
import logger

ACTIVE_SUBREDDITS = [
    'testingground4bots',
    'YangForPresidentHQ',
    'YangGang',
    'yangformayorhq',
    'BasicIncome',
    'nyc',
    'newyorkcity',
    'Futurology',
]

FOOTER = "^Beep ^Boop! ^I'm ^a ^bot! ^Bugs? ^Feedback? "\
    "^Contact ^my ^[author](https://www.reddit.com/message/compose?to=k_joel&subject=[yangbot]) "\
    "^or ^join ^the ^[discussion](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/). "\
    "^The ^[source](https://github.com/k-joel/yangbot)."

SHORT_ERROR = "Sorry, I was unable to process your query. The query length should be atleast 3 characters or more. Please try again."

MATCH_ERROR = "Sorry, I couldn't find a match for your query \'%s\'.\n\n"\
    "If you think this is an error or you wish to add this phrase to the related keyword list,"\
    " please comment [here](https://www.reddit.com/user/yangpolicyinfo_bot/comments/kw56cu/discussion_thread/)"

COMMAND_Y4NYC = '!yangbot'
COMMAND_Y2020 = '!yangbot-2020'
MIN_PHRASE_LEN = 2
CHARACTER_LIMIT = 9500

TEST_FILE = 'test.md'

LOGGER = logger.get_logger()


def dump_text_to_file(text):
    with open(TEST_FILE, 'w') as file:
        file.write(text)


def process_keywords(keywords):
    flattened = []
    for key, words in keywords.items():
        flattened += [(key, word) for word in words]
    return flattened


def resolve_keywords(phrase, processed_kws):
    match = process.extractOne(
        ("", phrase), processed_kws, processor=lambda x: x[1], score_cutoff=80)

    if not match:
        return phrase

    LOGGER.info('Resolved keyword \'%s\' to \'%s\'' % (phrase, match[0][0]))
    return match[0][0]


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
    if len(phrase) < MIN_PHRASE_LEN:
        return

    policies, policy_kws = policies_yang4nyc.get_policies_and_keywords()
    if not policies:
        return

    processed_kws = process_keywords(policy_kws)

    policy = match_policy(phrase, policies, processed_kws)
    if not policy:
        return

    texts = build_policy(policy)
    text = ''
    if len(texts) == 1:
        text = texts[0]
    else:
        for i, t in enumerate(texts):
            text += 'Part [%s / %s]\n\n%s' % (
                str(i+1), str(len(texts)), t)

    print(text)
    # dump_text_to_file(text)


def test_keywords():
    keywords = process_keywords(policies_yang4nyc.POLICY_KEYWORDS)
    while True:
        phrase = input("Input: ")
        if phrase == '':
            break
        title = resolve_keywords(phrase, keywords)


def main():
    LOGGER.info('--- Yangbot started ---')

    new_policies, new_policy_kws = policies_yang4nyc.get_policies_and_keywords()
    old_policies, old_policy_kws = policies_yang2020.get_policies_and_keywords()
    if not new_policies or not old_policies:
        return

    lookup = {
        COMMAND_Y4NYC: (new_policies, process_keywords(new_policy_kws)),
        COMMAND_Y2020: (old_policies, process_keywords(old_policy_kws))
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

        if len(comment.body) < len(COMMAND_Y4NYC) or\
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
                    # slow down to prevent spam
                    time.sleep(5)

        else:
            comment.author.message('Yangbot Error!', MATCH_ERROR % phrase)
            LOGGER.info('Failed match!')


def main_ex():
    while True:
        try:
            main()
        except Exception as e:
            LOGGER.critical('!!Exception raised!!\n' + str(e))
            LOGGER.critical('Restarting in 30 seconds...')
            time.sleep(30)
        else:
            LOGGER.info('--- Yangbot stopped ---')
            break


if __name__ == "__main__":
    #dev_main("strong recovery")
    # test_keywords()
    main_ex()
