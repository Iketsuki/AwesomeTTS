# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2015-2016  Anki AwesomeTTS Development Team
# Copyright (C) 2015-2016  Dave Shifflett
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

"""Service implementation for VoiceText's text-to-speech API"""

from .base import Service
from .common import Trait

__all__ = ['VoiceText']


VOICES = [
    ('show', "Show (male)"),
    ('takeru', "Takeru (male)"),
    ('haruka', "Haruka (female)"),
    ('hikari', "Hikari (female)"),
    ('bear', "a ferocious bear"),
    ('santa', "Santa Claus"),
]

EMOTIONAL_VOICES = ['bear', 'haruka', 'hikari', 'santa', 'takeru']


class VoiceText(Service):
    """Provides a Service-compliant implementation for VoiceText."""

    __slots__ = []

    NAME = "VoiceText"

    TRAITS = [Trait.INTERNET, Trait.TRANSCODING]

    def desc(self):
        """Returns a short, static description."""

        return "VoiceText Web API for Japanese (%d voices)" % len(VOICES)

    def options(self):
        """
        Provides access to voice, emotion, speed, pitch, and volume.

        Should also provide intensity, but appears to be broken on API.
        """

        return [
            dict(
                key='voice',
                label="Voice",
                values=VOICES,
                default='takeru',
                transform=self.normalize,
            ),

            dict(
                key='emotion',
                label="Emotion",
                values=[(value, value) for value in ['none', 'happiness',
                                                     'anger', 'sadness']],
                default='none',
                transform=self.normalize,
            ),

            # FIXME (and below in `parameters`): seems to trigger HTTP 400?
            #
            # If this does get added back, then the API on Google App Engine
            # must be updated to allow this parameter in through the sanity
            # checking code.
            #
            # dict(
            #     key='intensity',
            #     label="Intensity",
            #     values=[(1, "weak"), (2, "normal"),
            #             (3, "strong"), (4, "very strong")],
            #     default=2,
            #     transform=lambda value: min(max(int(float(value)), 1), 4),
            # ),

            dict(
                key='speed',
                label="Speed",
                values=(50, 400, "%"),
                transform=int,
                default=100,
            ),

            dict(
                key='pitch',
                label="Pitch",
                values=(50, 200, "%"),
                transform=int,
                default=100,
            ),

            dict(
                key='volume',
                label="Volume",
                values=(50, 200, "%"),
                transform=int,
                default=100,
            ),
        ]

    def run(self, text, options, path):
        """
        Downloads from VoiceText to an AAC file, then transcodes that
        into an MP3 via mplayer and lame.

        If the input text is longer than 100 characters, it will be
        split across multiple requests, transcoded, then merged back
        together into a single MP3.
        """

        aac_paths = []
        wav_paths = []
        mp3_paths = []

        parameters = dict(
            speaker=options['voice'],
            format='aac',
            # emotion_level=options['intensity'],
            speed=options['speed'],
            pitch=options['pitch'],
            volume=options['volume'],
        )

        if options['emotion'] != 'none':
            if options['voice'] not in EMOTIONAL_VOICES:
                raise IOError(
                    "The '%s' VoiceText voice does not allow emotion to be "
                    "applied; choose another voice (any of %s), or set the "
                    "emotion to 'none'." % (options['voice'],
                                            ", ".join(EMOTIONAL_VOICES))
                )
            parameters['emotion'] = options['emotion']

        try:
            api_endpoint = self.ecosystem.web + '/api/voicetext'

            for subtext in self.util_split(text, 100):
                # n.b. We call net_dump() using a local file path after calling
                # net_download() instead of just calling net_dump() directly w/
                # the URL so we can get direct access to HTTP status codes from
                # net_download() (e.g. if our VoiceText proxy rejects the call)

                aac_path = self.path_temp('aac')
                aac_paths.append(aac_path)
                parameters['text'] = subtext
                self.net_download(aac_path,
                                  (api_endpoint, parameters),
                                  require=dict(mime='audio/aac', size=256),
                                  awesome_ua=True)

                wav_path = self.path_temp('wav')
                wav_paths.append(wav_path)
                self.net_dump(wav_path, aac_path)

            if len(wav_paths) > 1:
                for wav_path in wav_paths:
                    mp3_path = self.path_temp('mp3')
                    mp3_paths.append(mp3_path)
                    self.cli_transcode(wav_path, mp3_path)
                self.util_merge(mp3_paths, path)

            else:
                self.cli_transcode(wav_paths[0], path)

        finally:
            self.path_unlink(aac_paths, wav_paths, mp3_paths)
