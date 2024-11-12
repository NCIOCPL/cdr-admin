#!/usr/bin/env python

"""Dump the server environment variables as json. Requires permission.
"""

from json import dumps
from os import environ
from cdrcgi import Controller

control = Controller(subtitle="Dump Environment")
if not control.session.can_do("GET SYS CONFIG"):
    control.bail("go away")
control.send_page(dumps(dict(environ), indent=2), mime_type="application/json")
