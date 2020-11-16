# Copyright (c) 2020, LE GOFF Vincent
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

"""Character entity, a playing character or non-playing character alike."""

import inspect
from datetime import datetime
import pickle

from pony.orm import Optional, Required, Set

from command.layer import StaticCommandLayer
from command.stack import CommandStack
from data.base import db, PicklableEntity
from data.decorators import lazy_property
from data.handlers import (
        AttributeHandler, LocatorHandler, PermissionHandler,
        NameHandler, TagHandler)
from scripting.variable import VariableFormatter
import settings

class Character(PicklableEntity, db.Entity):

    """Character entity."""

    name = Required(str, max_len=128)
    session = Optional("Session")
    account = Optional("Account")
    created_on = Required(datetime, default=datetime.utcnow)
    db_command_stack = Optional(bytes)

    @lazy_property
    def db(self):
        return AttributeHandler(self)

    @lazy_property
    def tags(self):
        return TagHandler(self)

    @lazy_property
    def locator(self):
        return LocatorHandler(self)

    @lazy_property
    def permissions(self):
        return PermissionHandler(self)

    @lazy_property
    def location(self):
        return self.locator.get()

    @location.setter
    def location(self, new_location):
        self.locator.set(new_location)

    @property
    def contents(self):
        return self.locator.contents()

    @lazy_property
    def names(self):
        return NameHandler(self)

    @classmethod
    def init_script(cls):
        """Initialize the script of characters, adding events."""
        cls.add_scripting_event(
                "login"
        ).set_help("""
                When a character logs in or is controlled by a player.
                This scripting event is called after a player has connected to this character, either has part of standard login, or after an admin has taken control of this character.
        """)

    async def move_to(self, exit):
        """Move to the specified exit."""
        self.location = exit.destination_for(self.location)
        await self.msg(self.location.look(self))

    @lazy_property
    def command_stack(self):
        """Return the stored or newly-bulid command stack."""
        stored = self.db_command_stack
        if stored:
            return pickle.loads(stored)

        # Create a new command stack
        stack = CommandStack(self)
        # Add the static command layer as first layer
        stack.add_layer(StaticCommandLayer)
        return stack

    async def msg(self, text, variables=None):
        """
        Send text to the connected session, if any.

        """
        formatter = VariableFormatter(self, variables)
        text = formatter.format(text)
        if self.session:
            await self.session.msg(text)
