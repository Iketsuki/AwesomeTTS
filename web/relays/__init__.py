# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on website
#
# Copyright (C) 2015-2016  Anki AwesomeTTS Development Team
# Copyright (C) 2015-2016  Dave Shifflett
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

from json import dumps as _json
from logging import error as _error, warning as _warn
from urllib2 import urlopen as _url_open, Request as _Request

__all__ = ['voicetext']


# n.b. When adding additional mustached-in variables, add a build-time check
# for `KEYS_RELAYS_MISSING` in ../Gruntfile.js so nothing gets missed during a
# deployment.

# For auth, VoiceText uses API key as the "username" w/ blank password, e.g.:
# import base64; 'Basic ' + base64.encodestring('someapikey123' + ':').strip()
_API_VOICETEXT_AUTH = dict(Authorization='{{{voicetext}}}')
_API_VOICETEXT_ENDPOINT = 'https://api.voicetext.jp/v1/tts'
_API_VOICETEXT_TIMEOUT = 10

_AWESOMETTS = 'AwesomeTTS/'

_CODE_200 = '200 OK'
_CODE_400 = '400 Bad Request'
_CODE_403 = '403 Forbidden'
_CODE_405 = '405 Method Not Allowed'
_CODE_502 = '502 Bad Gateway'

_HEADERS_JSON = [('Content-Type', 'application/json')]
_HEADERS_WAVE = [('Content-Type', 'audio/wave')]


def _get_message(msg):
    "Returns a list-of-one-string payload for returning from handlers."
    return [_json(dict(message=msg), separators=(',', ':'))]

_MSG_DENIED = _get_message("You may not call this endpoint directly")
_MSG_UNACCEPTABLE = _get_message("Your request is unacceptable")
_MSG_UPSTREAM = _get_message("Cannot communicate with upstream service")


def voicetext(environ, start_response):
    """
    After validating the incoming request, retrieve the wave file from
    the upstream VoiceText service, check it, and return it.
    """

    if not environ.get('HTTP_USER_AGENT', '').startswith(_AWESOMETTS):
        _warn("Relay denied -- unauthorized user agent")
        start_response(_CODE_403, _HEADERS_JSON)
        return _MSG_DENIED

    if environ.get('REQUEST_METHOD') != 'GET':
        _warn("Relay denied -- unacceptable request method")
        start_response(_CODE_405, _HEADERS_JSON)
        return _MSG_UNACCEPTABLE

    data = environ.get('QUERY_STRING')

    # do a very rough sanity check without generating a bunch of junk objects;
    # remember that most Japanese characters encode to 9-byte strings and we
    # allow up to 100 Japanese characters (or 900 bytes) in the client
    if not (data and len(data) < 1000 and data.count('&') > 4 and
            data.count('=') < 8 and 'format=wav' in data and
            'pitch=' in data and 'speaker=' in data and 'speed=' in data and
            'text=' in data and 'volume=' in data):
        _warn("Relay denied -- unacceptable query string")
        start_response(_CODE_400, _HEADERS_JSON)
        return _MSG_UNACCEPTABLE

    try:
        response = _url_open(_Request(_API_VOICETEXT_ENDPOINT, data,
                                      _API_VOICETEXT_AUTH),
                             timeout=_API_VOICETEXT_TIMEOUT)

        if response.getcode() != 200:
            raise IOError("non-200 status code from upstream service")

        if response.info().gettype() != 'audio/wave':
            raise IOError("non-audio/wave format from upstream service")

        payload = [response.read()]

    except Exception as exception:  # catch all, pylint:disable=broad-except
        _error("Relay failed -- %s", exception)
        start_response(_CODE_502, _HEADERS_JSON)
        return _MSG_UPSTREAM

    else:
        start_response(_CODE_200, _HEADERS_WAVE)
        return payload

    finally:
        try:
            response.close()
        except Exception:  # catch all, pylint:disable=broad-except
            pass
