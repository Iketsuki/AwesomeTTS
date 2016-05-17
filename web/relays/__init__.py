# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on website
#
# Copyright (C) 2015       Anki AwesomeTTS Development Team
# Copyright (C) 2015       Dave Shifflett
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
WSGI callables for service relays

Handlers here provide a way for users of the add-on to access certain
services that cannot be communicated with directly (e.g. text-to-speech
APIs that require authenticated access).
"""

__all__ = ['voicetext']

from json import dumps as _json


_CODE_503 = '503 Service Unavailable'

_HEADERS_JSON = [('Content-Type', 'application/json')]


def _get_message(msg):
    "Returns a list-of-one-string payload for returning from handlers."
    return [_json(dict(message=msg), separators=(',', ':'))]

_MSG_UNAVAILABLE = _get_message("VoiceText access is temporarily unavailable")


def voicetext(environ, start_response):
    """Return an HTTP 503."""

    start_response(_CODE_503, _HEADERS_JSON)
    return _MSG_UNAVAILABLE
