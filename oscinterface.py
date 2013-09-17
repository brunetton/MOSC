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

import interface
import pysc


class OSCInterface(interface.Interface):
    def __init__(self, server_address, client_address=None):
        super(OSCInterface, self).__init__()
        self.server_address = "0.0.0.0", server_address if isinstance(server_address, int) else server_address
        self.server = pysc.Server(self.server_address, self._message_handler)
        self.client = None if client_address is None else pysc.Client(client_address)

    def send(self, address, *value):
        if self.client is None:
            return
        self.client.send(pysc.Message(address, *value))

    def _run(self):
        self.server.serve_forever()

    def _message_handler(self, message, client_address):
        if self.client is None:
            self.client = pysc.Client((client_address[0], self.server_address[1]))

        if self.handler is None:
            return

        self.handler(message.address, *message.args)