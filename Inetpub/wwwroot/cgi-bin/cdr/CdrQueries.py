#!/usr/bin/python
#----------------------------------------------------------------------
#
# $Id$
#
# Ad-hoc SQL query tool for CDR database.
#
#----------------------------------------------------------------------

import CgiQuery, cdrdb

class CdrQuery(CgiQuery.CgiQuery):
    def __init__(self):
        conn = cdrdb.connect('CdrGuest')
        CgiQuery.CgiQuery.__init__(self, conn, "CDR", "CdrQueries.py", 600)

cdrQuery = CdrQuery()
cdrQuery.run()
