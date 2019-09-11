#!/usr/bin/python
#----------------------------------------------------------------------
# Ad-hoc SQL query tool for CDR database.
#----------------------------------------------------------------------

import CgiQuery
from cdrapi import db

class CdrQuery(CgiQuery.CgiQuery):
    def __init__(self):
        conn = db.connect(user="CdrGuest", timeout=600)
        CgiQuery.CgiQuery.__init__(self, conn, "CDR", "CdrQueries.py")

cdrQuery = CdrQuery()
cdrQuery.run()
