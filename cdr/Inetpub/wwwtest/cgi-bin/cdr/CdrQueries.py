#!/usr/bin/python
#----------------------------------------------------------------------
#
# $Id: CdrQueries.py,v 1.1 2002-12-10 13:34:06 bkline Exp $
#
# Ad-hoc SQL query tool for CDR database.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import CgiQuery, cdrdb

class CdrQuery(CgiQuery.CgiQuery):
    def __init__(self):
        conn = cdrdb.connect('CdrGuest')
        CgiQuery.CgiQuery.__init__(self, conn, "CDR", "CdrQueries.py")

cdrQuery = CdrQuery()
cdrQuery.run()
