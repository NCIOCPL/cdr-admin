#!/usr/bin/python
#----------------------------------------------------------------------
#
# $Id: CdrQueries.py,v 1.3 2005-12-13 14:41:38 bkline Exp $
#
# Ad-hoc SQL query tool for CDR database.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2003/11/05 14:47:14  bkline
# Increased timeout to 5 minutes.
#
# Revision 1.1  2002/12/10 13:34:06  bkline
# Add-hoc SQL query tool for CDR database.
#
#----------------------------------------------------------------------

import CgiQuery, cdrdb

class CdrQuery(CgiQuery.CgiQuery):
    def __init__(self):
        conn = cdrdb.connect('CdrGuest')
        CgiQuery.CgiQuery.__init__(self, conn, "CDR", "CdrQueries.py", 600)

cdrQuery = CdrQuery()
cdrQuery.run()
