# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2010-2014  Anki AwesomeTTS Development Team
# Copyright (C) 2010-2012  Arthur Helfstein Fragoso
# Copyright (C) 2013-2014  Dave Shifflett
# Copyright (C) 2013       mistaecko on GitHub
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
Service implementation for Google Translate's text-to-speech API
"""

__all__ = ['Google']

from .base import Service
from .common import Trait


class Google(Service):
    """
    Provides a Service-compliant implementation for Google Translate.
    """

    # FIXME. This service currently only supports short phrases.
    # See https://github.com/AwesomeTTS/AwesomeTTS/issues/21
    # Once fixed, the text returned by desc() should be updated.

    __slots__ = [
    ]

    NAME = "Google Translate"

    TRAITS = [Trait.INTERNET]

    _VOICE_CODES = {
        # n.b. When modifying any variants, make sure that there are
        # aliases defined in the voice_lookup list below for the most
        # common alternate codes, including an alias from the base
        # language to the variant with the most native speakers.

        'af': "Afrikaans", 'ar': "Arabic", 'bs': "Bosnian", 'ca': "Catalan",
        'cs': "Czech", 'cy': "Welsh", 'da': "Danish", 'de': "German",
        'el': "Greek", 'en-AU': "English, Australian",
        'en-GB': "English, British", 'en-US': "English, American",
        'eo': "Esperanto", 'es-419': "Spanish, Americas",
        'es-ES': "Spanish, European", 'fi': "Finnish", 'fr': "French",
        'hi': "Hindi", 'hr': "Croatian", 'ht': "Haitian Creole",
        'hu': "Hungarian", 'hy': "Armenian", 'id': "Indonesian",
        'is': "Icelandic", 'it': "Italian", 'ja': "Japanese", 'ko': "Korean",
        'la': "Latin", 'lv': "Latvian", 'mk': "Macedonian", 'nl': "Dutch",
        'no': "Norwegian", 'pl': "Polish", 'pt-BR': "Portuguese, Brazilian",
        'pt-PT': "Portuguese, European", 'ro': "Romanian", 'ru': "Russian",
        'sk': "Slovak", 'sq': "Albanian", 'sr': "Serbian", 'sv': "Swedish",
        'sw': "Swahili", 'ta': "Tamil", 'th': "Thai", 'tr': "Turkish",
        'vi': "Vietnamese", 'zh-CMN': "Chinese, Mandarin",
        'zh-YUE': "Chinese, Cantonese",
    }

    def desc(self):
        """
        Returns a short, static description.
        """

        return "Google Translate text-to-speech web API " \
            "(%d voices, short phrases only)" % len(self._VOICE_CODES)

    def options(self):
        """
        Provides access to voice only.
        """

        voice_list = sorted([
            (code, "%s (%s)" % (name, code))
            for code, name in self._VOICE_CODES.items()
        ], key=lambda voice: voice[1])

        voice_lookup = dict([
            # aliases for Chinese, Cantonese (fewer speakers)
            (self.normalize(alias), 'zh-YUE')
            for alias in ['Cantonese', 'zh-TW', 'YUE']
        ] + [
            # aliases for Chinese, Mandarin (most speakers)
            (self.normalize(alias), 'zh-CMN')
            for alias in ['Mandarin', 'Chinese', 'zh', 'zh-CN', 'CMN']
        ] + [
            # aliases for Spanish, European (fewer speakers)
            (self.normalize(alias), 'es-ES')
            for alias in ['es-EU']
        ] + [
            # aliases for Spanish, Americas (most speakers)
            (self.normalize(alias), 'es-419')
            for alias in ['Spanish', 'es', 'es-LA', 'es-MX', 'es-US']
        ] + [
            # aliases for English, Australian (fewer speakers)
            (self.normalize(alias), 'en-AU')
            for alias in ['en-NZ']
        ] + [
            # aliases for English, British (moderate number)
            (self.normalize(alias), 'en-GB')
            for alias in ['en-EU', 'en-UK']
        ] + [
            # aliases for English, American (most speakers)
            (self.normalize(alias), 'en-US')
            for alias in ['English', 'en']
        ] + [
            # aliases for Portuguese, European (fewer speakers)
            (self.normalize(alias), 'pt-PT')
            for alias in ['pt-EU']
        ] + [
            # aliases for Portuguese, Brazilian (most speakers)
            (self.normalize(alias), 'pt-BR')
            for alias in ['Portuguese', 'pt']
        ] + [
            # then add/override for full names (e.g. Spanish, Americas)
            (self.normalize(name), code)
            for code, name in self._VOICE_CODES.items()
        ] + [
            # then add/override for official voices (e.g. es-419)
            (self.normalize(code), code)
            for code in self._VOICE_CODES.keys()
        ])

        def transform_voice(value):
            """Normalize and attempt to convert to official code."""

            normalized = self.normalize(value)
            if normalized in voice_lookup:
                return voice_lookup[normalized]

            # if input is more than two characters, maybe the user was trying
            # a country-specific code (e.g. es-CO); chop it off and try again
            if len(normalized) > 2:
                normalized = normalized[0:2]
                if normalized in voice_lookup:
                    return voice_lookup[normalized]

            return value

        return [
            dict(
                key='voice',
                label="Voice",
                values=voice_list,
                transform=transform_voice,
            ),
        ]

    def run(self, text, options, path):
        """
        Downloads from Google directly to an MP3.

        Because the MP3 get from Google is already so very tiny, LAME is
        not used for transcoding.
        """

        self.net_download(
            path=path,
            addr='http://translate.google.com/translate_tts',
            query=dict(
                tl=options['voice'],
                q=text,
            ),
            require=dict(
                status=200,
                mime='audio/mpeg',
                size=1024,
            ),
        )
