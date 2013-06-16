"""
Copyright (c) 2013 by Tomer Altman <tomer.altman@gmail.com>

This file is part of MOSC.

MOSC is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MOSC is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with MOSC.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
import threading

class Interface(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        self.handler = None

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    @abc.abstractmethod
    def send(self, address, value):
        pass

    @abc.abstractmethod
    def _run(self):
        pass
