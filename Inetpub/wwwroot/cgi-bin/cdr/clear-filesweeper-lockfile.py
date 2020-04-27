#!/usr/bin/env python

#----------------------------------------------------------------------
# Release lock blocking future Hoover runs.
# JIRA::OCECDR-4196
#----------------------------------------------------------------------
import cgi
import os
import cdr
import cdrcgi

PATH = f"{cdr.DEFAULT_LOGDIR}/FileSweeper.lockfile"

def report(what):
    print(f"Content-type: text/plain\n\n{what}")

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not session or not cdr.canDo(session, "MANAGE SCHEDULER"):
    report("Not authorized")
elif os.path.exists(PATH):
    try:
        os.unlink(PATH)
        report("Lock file removed")
    except:
        report("Unable to remove lock file")
else:
    report("Lock file not found")
