# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2014-2016  Anki AwesomeTTS Development Team
# Copyright (C) 2014-2016  Dave Shifflett
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Basic manipulation and sanitization of input text
"""

__all__ = ['RE_CLOZE_BRACED', 'RE_CLOZE_RENDERED', 'RE_ELLIPSES',
           'RE_ELLIPSES_LEADING', 'RE_ELLIPSES_TRAILING', 'RE_FILENAMES',
           'RE_HINT_LINK', 'RE_LINEBREAK_HTML', 'RE_NEWLINEISH', 'RE_SOUNDS',
           'RE_WHITESPACE', 'STRIP_HTML', 'Sanitizer']

from random import random
import re
from StringIO import StringIO

from BeautifulSoup import BeautifulSoup
import anki


RE_CLOZE_BRACED = re.compile(anki.template.template.clozeReg % r'\d+')
RE_CLOZE_RENDERED = re.compile(
    # see anki.template.template.clozeText; n.b. the presence of the brackets
    # in the pattern means that this will only match and replace on the
    # question side of cards
    r'<span class=.?cloze.?>\[(.+?)\]</span>'
)
RE_ELLIPSES = re.compile(r'\s*(\.\s*){3,}')
RE_ELLIPSES_LEADING = re.compile(r'^\s*(\.\s*){3,}')
RE_ELLIPSES_TRAILING = re.compile(r'\s*(\.\s*){3,}$')
RE_FILENAMES = re.compile(r'([a-z\d]+(-[a-f\d]{8}){5}|ATTS .+)'
                          r'( \(\d+\))?\.mp3')
RE_HINT_LINK = re.compile(r'<a[^>]+class=.?hint.?[^>]*>[^<]+</a>')
RE_LINEBREAK_HTML = re.compile(r'<\s*/?\s*(br|div|p)(\s+[^>]*)?\s*/?\s*>',
                               re.IGNORECASE)
RE_NEWLINEISH = re.compile(r'(\r|\n|<\s*/?\s*(br|div|p)(\s+[^>]*)?\s*/?\s*>)+',
                           re.IGNORECASE)
RE_SOUNDS = re.compile(r'\[sound:(.*?)\]')  # see also anki.sound._soundReg
RE_WHITESPACE = re.compile(r'[\0\s]+', re.UNICODE)

STRIP_HTML = anki.utils.stripHTML  # this also converts character entities


class Sanitizer(object):  # call only, pylint:disable=too-few-public-methods
    """Once instantiated, provides a callable to sanitize text."""

    # _rule_xxx() methods are in-class for getattr, pylint:disable=no-self-use

    __slots__ = [
        '_config',  # dict-like interface for looking up config conditionals
        '_logger',  # logger-like interface for debugging the Sanitizer
        '_rules',   # list of rules that this instance's callable will process
    ]

    def __init__(self, rules, config=None, logger=None):
        self._rules = rules
        self._config = config
        self._logger = logger

    def __call__(self, text):
        """Apply the initialized rules against the text and return."""

        applied = []

        for rule in self._rules:
            if not text:
                self._log(applied + ["early exit"], '')
                return ''

            if isinstance(rule, basestring):  # always run these rules
                applied.append(rule)
                text = getattr(self, '_rule_' + rule)(text)

            elif isinstance(rule, tuple):  # rule that depends on config
                try:
                    addl = rule[2]
                except IndexError:
                    addl = None
                key = rule[1]
                rule = rule[0]

                # if the "key" is actually a list, then we will return True
                # for `value` if ANY key in the list yields a truthy config
                value = (next((True for k in key if self._config[k]),
                              False) if isinstance(key, list)
                         else self._config[key])

                if value is True:  # basic on/off config flag
                    if addl:
                        addl = [self._config[addl_key] for addl_key in addl] \
                            if isinstance(addl, list) else self._config[addl]
                        applied.append((rule, addl))
                        text = getattr(self, '_rule_' + rule)(text, addl)

                    else:
                        applied.append(rule)
                        text = getattr(self, '_rule_' + rule)(text)

                elif value:  # some other truthy value that drives the rule
                    if addl:
                        addl = [self._config[addl_key] for addl_key in addl] \
                            if isinstance(addl, list) else self._config[addl]
                        applied.append((rule, value, addl))
                        text = getattr(self, '_rule_' + rule)(text, value,
                                                              addl)

                    else:
                        applied.append((rule, value))
                        text = getattr(self, '_rule_' + rule)(text, value)

            else:
                raise AssertionError("bad rule given to Sanitizer instance")

        self._log(applied, text)
        return text

    def _log(self, method, result):
        """If we have a logger, send debug line for transformation."""

        if self._logger:
            self._logger.debug("Transformation using %s: %s", method,
                               "(empty string)" if result == '' else result)

    def _rule_char_ellipsize(self, text, chars):
        """Ellipsizes given chars from the text."""

        return ''.join(
            ('...' if char in chars else char)
            for char in text
        )

    def _rule_char_remove(self, text, chars):
        """Removes given chars from the text."""

        return ''.join(char for char in text if char not in chars)

    def _rule_clozes_braced(self, text, mode):
        """
        Given a braced cloze placeholder in a note, examine the option
        mode and return an appropriate replacement.
        """

        return RE_CLOZE_BRACED.sub(
            '...' if mode == 'ellipsize'
            else '' if mode == 'remove'
            else self._rule_clozes_braced.wrapper if mode == 'wrap'
            else self._rule_clozes_braced.deleter if mode == 'deleted'
            else self._rule_clozes_braced.ankier,  # mode == 'anki'

            text,
        )

    _rule_clozes_braced.wrapper = lambda match: (
        '... %s ...' % match.group(3).strip('.') if (match.group(3) and
                                                     match.group(3).strip('.'))
        else '...'
    )

    _rule_clozes_braced.deleter = lambda match: (
        match.group(1) if match.group(1)
        else '...'
    )

    _rule_clozes_braced.ankier = lambda match: (
        match.group(3) if match.group(3)
        else '...'
    )

    def _rule_clozes_rendered(self, text, mode):
        """
        Given a rendered cloze HTML tag, examine the option mode and
        return an appropriate replacement.
        """

        return RE_CLOZE_RENDERED.sub(
            '...' if mode == 'ellipsize'
            else '' if mode == 'remove'
            else self._rule_clozes_rendered.wrapper if mode == 'wrap'
            else self._rule_clozes_rendered.ankier,  # mode == 'anki'

            text,
        )

    _rule_clozes_rendered.wrapper = lambda match: (
        '... %s ...' % match.group(1).strip('.')
        if match.group(1).strip('.')
        else match.group(1)
    )

    _rule_clozes_rendered.ankier = lambda match: match.group(1)

    def _rule_clozes_revealed(self, text, (want_before, want_before_until,
                                           want_after, want_after_until)):
        """
        Given text that has a revealed cloze span, return only the
        contents of that span, or if before/after context is enabled,
        the contents of that span plus the necessary tokens before and
        after the matching span.

        Note that when used with before/after context, this rule may
        destroy surrounding markup, so following rules should not depend
        on any markup being present.
        """

        soup = BeautifulSoup(text)
        revealed_tags = soup('span', attrs={'class': 'cloze'})

        if revealed_tags:
            revealed_texts = []

            for i, revealed_tag in enumerate(revealed_tags):
                revealed_text = revealed_tag.text

                if want_before or want_after:
                    revealed_tag['id'] = 'split-' + unicode(i + random())
                    all_html = unicode(soup)
                    split_html = unicode(revealed_tag)
                    html_before, html_after = all_html.split(split_html)

                    if want_before and html_before:
                        text_before = self._rule_html(html_before)

                        if text_before:
                            space_before = text_before[-1].isspace()
                            tokens_before = text_before.split()
                            if want_before_until:
                                for j, token in reversed(list(enumerate(
                                        tokens_before))):
                                    if token[-1] in want_before_until:
                                        tokens_before = tokens_before[j + 1:]
                                        break
                            ctx_before = ' '.join(tokens_before[-want_before:])
                            if space_before:
                                ctx_before += ' '
                            revealed_text = ctx_before + revealed_text

                    if want_after and html_after:
                        text_after = self._rule_html(html_after)

                        if text_after:
                            space_after = text_after[0].isspace()
                            tokens_after = text_after.split()
                            if want_after_until:
                                for j, token in enumerate(tokens_after):
                                    if token[-1] in want_after_until:
                                        tokens_after = tokens_after[:j + 1]
                                        break
                            ctx_after = ' '.join(tokens_after[0:want_after])
                            if space_after:
                                ctx_after = ' ' + ctx_after
                            revealed_text += ctx_after

                revealed_texts.append(revealed_text)

            return ' ... '.join(revealed_texts)

        else:
            return text

    def _rule_counter(self, text, characters, wrap):
        """
        Upon encountering the given characters, replace with the number
        of those characters that were encountered.
        """

        return re.sub(
            r'[' + re.escape(characters) + ']{2,}',

            self._rule_counter.wrapper if wrap
            else self._rule_counter.spacer,

            text,
        )

    _rule_counter.wrapper = lambda match: (' ... ' + str(len(match.group(0))) +
                                           ' ... ')

    _rule_counter.spacer = lambda match: (' ' + str(len(match.group(0))) + ' ')

    def _rule_custom_sub(self, text, rules):
        """
        Upon encountering text that matches one of the user's compiled
        rules, make a replacement. Run whitespace and ellipsis rules
        before each one.
        """

        for rule in rules:
            text = self._rule_whitespace(self._rule_ellipses(text))
            if not text:
                return ''

            text = rule['compiled'].sub(rule['replace'], text)
            if not text:
                return ''

        return text

    def _rule_ellipses(self, text):
        """
        Given at least three periods, separated by whitespace or not,
        collapse down to three consecutive periods padded on both sides.

        Additionally, drop any leading or trailing ellipses entirely.
        """

        text = RE_ELLIPSES.sub(' ... ', text)
        text = RE_ELLIPSES_LEADING.sub(' ', text)
        text = RE_ELLIPSES_TRAILING.sub(' ', text)
        return text

    def _rule_filenames(self, text):
        """
        Removes any filenames that appear to be from AwesomeTTS.
        """

        return RE_FILENAMES.sub('', text)

    def _rule_hint_content(self, text):
        """
        Removes hint content from the use of a {{hint:xxx}} field.
        """

        soup = BeautifulSoup(text)
        hints = soup.findAll('div', attrs={'class': 'hint'})
        while hints:
            hints.pop().extract()

        return unicode(soup)

    def _rule_hint_links(self, text):
        """
        Removes hint links from the use of a {{hint:XXX}} field.
        """

        return RE_HINT_LINK.sub('', text)

    def _rule_html(self, text):
        """
        Removes any HTML, including converting character entities.
        """

        text = RE_LINEBREAK_HTML.sub(' ', text)
        return STRIP_HTML(text)

    def _rule_newline_ellipsize(self, text):
        """
        Replaces linefeeds, newlines, and things that look like that
        (e.g. paragraph tags, div containers) with an ellipsis.
        """

        return RE_NEWLINEISH.sub(' ... ', text)

    def _rule_sounds_ours(self, text):
        """
        Removes sound tags that appear to be from AwesomeTTS.
        """

        return RE_SOUNDS.sub(
            lambda match: (
                '' if RE_FILENAMES.match(match.group(1))
                else match.group(0)
            ),
            text,
        )

    def _rule_sounds_theirs(self, text):
        """
        Removes sound tags that appear to NOT be from AwesomeTTS.
        """

        return RE_SOUNDS.sub(
            lambda match: (
                match.group(0) if RE_FILENAMES.match(match.group(1))
                else ''
            ),
            text,
        )

    def _rule_sounds_univ(self, text):
        """
        Removes sound tags, regardless of origin.
        """

        return RE_SOUNDS.sub('', text)

    def _rule_whitespace(self, text):
        """
        Collapses all whitespace down to a single space and strips
        off any leading or trailing whitespace.
        """

        return RE_WHITESPACE.sub(' ', text).strip()

    _rule_within_braces = lambda self, text: _aux_within(text, '{', '}')

    _rule_within_brackets = lambda self, text: _aux_within(text, '[', ']')

    _rule_within_parens = lambda self, text: _aux_within(text, '(', ')')


def _aux_within(text, begin_char, end_char):
    """
    Removes any substring of text that starts with begin_char and
    ends with end_char.
    """

    changed = False
    result = StringIO()
    sequences = []

    for char in text:
        if char == begin_char:  # begins new level of text to possibly cut
            sequence = StringIO()
            sequence.write(char)
            sequences.append(sequence)

        elif char == end_char:
            if sequences:  # match the last opening char and cut this text
                changed = True
                sequences.pop().close()

            else:  # include closing chars w/o matching opening in result
                result.write(char)

        elif sequences:  # write regular chars to current sequence level
            sequences[-1].write(char)

        else:  # write top-level regular chars to the result
            result.write(char)

    if changed:  # replace passed text object with the buffer
        for sequence in sequences:  # include stuff lacking a closing char
            result.write(sequence.getvalue())
        text = result.getvalue()

    result.close()
    while sequences:
        sequences.pop().close()

    return text
