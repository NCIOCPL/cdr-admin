#----------------------------------------------------------------------
#
# $Id: IEBugRepro.py,v 1.1 2002-07-18 01:05:25 bkline Exp $
#
# Repro case for bug in Internet Explorer which mistakes XML files
# for HTML files if it thinks it sees an HTML tag in the document
# (such as <PreferredTerm>, which looks too much like <PRE> for
# IE), even if the XML declaration and the Content-type header are
# present.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

print """\
Content-type: text/xml

<?xml version="1.0"?>
<Term>
  <PreferredTerm>Breast Cancer</PreferredTerm>
</Term>"""
