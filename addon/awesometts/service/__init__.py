# -*- coding: utf-8 -*-
# pylint:disable=bad-continuation

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
Service classes for AwesomeTTS
"""

__all__ = [
    # common
    'Trait',

    # services
    'Acapela',
    'Baidu',
    'Ekho',
    'ESpeak',
    'Festival',
    'FluencyNl',
    'Google',
    'Howjsay',
    'ImTranslator',
    'Naver',
    'NeoSpeech',
    'Oddcast',
    'Oxford',
    'Pico2Wave',
    'RHVoice',
    'SAPI5',
    'SAPI5JS',
    'Say',
    'SpanishDict',
    'VoiceText',
    'Yandex',
    'Youdao',
]

from .common import Trait

from .acapela import Acapela
from .baidu import Baidu
from .ekho import Ekho
from .espeak import ESpeak
from .festival import Festival
from .fluencynl import FluencyNl
from .google import Google
from .howjsay import Howjsay
from .imtranslator import ImTranslator
from .naver import Naver
from .neospeech import NeoSpeech
from .oddcast import Oddcast
from .oxford import Oxford
from .pico2wave import Pico2Wave
from .rhvoice import RHVoice
from .sapi5 import SAPI5
from .sapi5js import SAPI5JS
from .say import Say
from .spanishdict import SpanishDict
from .voicetext import VoiceText
from .yandex import Yandex
from .youdao import Youdao
