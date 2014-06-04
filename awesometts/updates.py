# -*- coding: utf-8 -*-
# pylint:disable=bad-continuation

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2014       Anki AwesomeTTS Development Team
# Copyright (C) 2014       Dave Shifflett
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
Update detection and callback handling
"""

__all__ = ['Updates']

from PyQt4 import QtCore, QtGui


_SERVICE_URL = 'https://ankiatts.appspot.com/update/%(token)s'

_SIGNAL_NEED = QtCore.SIGNAL('awesomeTtsUpdateNeeded')
_SIGNAL_GOOD = QtCore.SIGNAL('awesomeTtsUpdateGood')
_SIGNAL_FAIL = QtCore.SIGNAL('awesomeTtsUpdateFailure')


class Updates(QtGui.QWidget):
    """
    Handles managing a thread and executing callbacks when checking for
    updates.
    """

    __slots__ = [
        '_logger',        # reference to something w/ logging-like interface
        '_token',         # machine-readable updater token for URL
        '_callbacks',     # dict lookup of possible callbacks
        '_got_finished',  # True if the worker is "finished"
        '_got_signal',    # True if we've actually gotten a signal back
        '_worker',        # reference to the current worker
    ]

    def __init__(self, logger, token):
        """
        Initializes the update checker with a logger and the token for
        use when constructing the URL.
        """

        super(Updates, self).__init__()

        self._logger = logger
        self._token = token

        self._callbacks = None
        self._got_finished = None
        self._got_signal = None
        self._worker = None

    def check(self, callbacks):
        """
        Runs an update check against web service in a background thread,
        with the following callbacks:

        - done: called as soon as thread finishes
        - fail: called for exceptions or oddities (exception passed)
        - good: called if add-on is up-to-date
        - need: called if update available (version, description passed)
        - then: called afterward

        The only required callback is 'need', as headless checks are
        free to ignore 'fail' and 'good' and would have no use for
        'done' or 'then'.
        """

        assert 'done' not in callbacks or callable(callbacks['done'])
        assert 'fail' not in callbacks or callable(callbacks['fail'])
        assert 'good' not in callbacks or callable(callbacks['good'])
        assert 'need' in callbacks and callable(callbacks['need'])
        assert 'then' not in callbacks or callable(callbacks['then'])

        self._try_reap()
        if self._worker:
            raise RuntimeError("An update check is already in progress")

        self._callbacks = callbacks
        self._got_finished = False
        self._got_signal = False
        self._worker = _Worker(self._logger, self._token)

        self.connect(self._worker, _SIGNAL_NEED, self._on_signal_need)
        self.connect(self._worker, _SIGNAL_GOOD, self._on_signal_good)
        self.connect(self._worker, _SIGNAL_FAIL, self._on_signal_fail)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self._logger.debug("Spawned worker to check for updates")

    def _on_signal(self, key, *args, **kwargs):
        """
        Called for all signals.

        Does an internal consistency check, calls the 'done' handler (if
        any), the associated handler for the specific signal ('fail',
        'good', or 'need', if any), calls the 'then' handler (if any),
        and finally tries to reap the worker (if possible).

        If the specific signal callback is supposed to take arguments,
        those may be passed after the specific signal's key.
        """

        assert self._worker and not self._got_signal, "already got signal"
        self._got_signal = True

        if 'done' in self._callbacks:
            self._callbacks['done']()

        if key in self._callbacks:
            self._callbacks[key](*args, **kwargs)

        if 'then' in self._callbacks:
            self._callbacks['then']()

        self._try_reap()

    def _on_signal_fail(self, exception=None, stack_trace=None):
        """
        Called when something goes wrong during an update check. This
        can include both things like download errors or successful
        transmission of JSON that has an null value for the update
        status.
        """

        self._logger.error(
            "Exception (%s) during update check\n%s",

            exception.message or "no message",

            "\n".join("!!! " + line for line in stack_trace.split("\n"))
            if isinstance(stack_trace, basestring)
            else "Stack trace unavailable",
        )

        self._on_signal('fail', exception)

    def _on_signal_good(self):
        """
        Called when the worker finds no update information.
        """

        self._logger.info("No updates are available")
        self._on_signal('good')

    def _on_signal_need(self, version, description):
        """
        Called when the worker finds information about a new version.

        Note that unlike the one used in self._token, the version used
        here is a human-readable one and not one for building a URL.
        """

        self._logger.warn("Update for %s available" % version)
        self._on_signal('need', version, description)

    def _on_finished(self):
        """
        Called when the thread is considered "finished", even if a
        signal has not be returned back yet.
        """

        assert self._worker and not self._got_finished, "already finished"
        self._got_finished = True

        self._try_reap()

    def _try_reap(self):
        """
        If our worker has both been reported "finished" and got its
        signal back us, we can reap it. We do not reap it until both of
        these happen, which avoids crashes.
        """

        if self._worker and self._got_finished and self._got_signal:
            self._callbacks = None
            self._got_finished = None
            self._got_signal = None
            self._worker = None

            self._logger.debug("Reaped updates worker")


class _Worker(QtCore.QThread):
    """
    Handles the actual downloading of the JSON payload, parsing it, and
    returning a response to the main thread via a signal.
    """

    __slots__ = [
        '_logger',        # reference to something w/ logging-like interface
        '_token',         # machine-readable updater token for URL
    ]

    def __init__(self, logger, token):
        """
        Initializes the worker with the logger and machine-readable
        token string from the creating instance.
        """

        super(_Worker, self).__init__()

        self._logger = logger
        self._token = token

    def run(self):
        """
        Attempt to download the JSON payload to check for a new version.
        """

        try:
            url = _SERVICE_URL % {'token': self._token}
            self._logger.debug("Downloading update JSON from %s", url)

            # TODO do an actual check here
            # TODO check for 'update' key:
            #     - true: pass back _SIGNAL_NEED w/ version, description
            #               (if either of these missing, then raise)
            #     - false: pass back _SIGNAL_GOOD
            #     - null, undefined, otherwise: raise

            raise NotImplementedError
            # self.emit(_SIGNAL_GOOD)
            # self.emit(_SIGNAL_NEED, "v1.0 Magic", "This update does stuff.")

        except Exception as exception:  # catch all, pylint:disable=W0703
            from traceback import format_exc
            self.emit(_SIGNAL_FAIL, exception, format_exc())
