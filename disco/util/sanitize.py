import re


# Zero width (non-rendering) space that can be used to escape mentions
ZERO_WIDTH_SPACE = u'\u200B'

# A grave-looking character that can be used to escape codeblocks
MODIFIER_GRAVE_ACCENT = u'\u02CB'

# Regex which matches all possible mention combinations, this may be over-zealous
#  but its better safe than sorry.
MENTION_RE = re.compile('<?([@|#][!|&]?[0-9]+|@everyone|@here)>?')


def _re_sub_mention(mention):
    mention = mention.group(1)
    if '#' in mention:
        return (u'#' + ZERO_WIDTH_SPACE).join(mention.split('#', 1))
    elif '@' in mention:
        return (u'@' + ZERO_WIDTH_SPACE).join(mention.split('@', 1))
    else:
        return mention


def S(text, escape_mentions=True, escape_codeblocks=False):
    if escape_mentions:
        text = MENTION_RE.sub(_re_sub_mention, text)

    if escape_codeblocks:
        text = text.replace('`', MODIFIER_GRAVE_ACCENT)

    return text
