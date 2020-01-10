#!/usr/bin/env python

"""Log the current user out of the CDR.
"""

import cgi
import cdrcgi

fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
cdrcgi.logout(session)
