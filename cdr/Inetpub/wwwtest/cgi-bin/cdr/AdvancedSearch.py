#----------------------------------------------------------------------
#
# $Id: AdvancedSearch.py,v 1.9 2009-05-06 03:21:57 ameyer Exp $
#
# Main menu for advanced search forms.
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2008/09/18 13:57:47  bkline
# Added Drug Information Summaries search.
#
# Revision 1.7  2006/05/04 13:27:09  bkline
# Added Media.
#
# Revision 1.6  2004/09/10 17:09:53  venglisc
# Added style for mouse-hover background color to be consistend with the
# change to the menus. (Bug 1331)
#
# Revision 1.5  2002/05/16 14:33:04  bkline
# Changed wording of menu for Person with locations.
#
# Revision 1.4  2002/02/22 02:18:58  bkline
# Added advanced search page for Documentation documents.
#
# Revision 1.3  2002/02/20 04:00:51  bkline
# Added menu item for GlossaryTerm search.
#
# Revision 1.2  2002/02/14 19:34:21  bkline
# Replaced Geographic Unit with Country and Political SubUnit choices.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdrcgi, urllib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields) or ""
session = "?%s=%s" % (cdrcgi.SESSION, session)
header  = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>Advanced Search Document Type Selection</TITLE>
  <META   HTTP-EQUIV = "Content-Type"
             CONTENT = "text/html; charset=iso-8859-1">
  <STYLE        TYPE = "text/css">
   <!--
    .Page { font-family: Arial, Helvetica, sans-serif;
            color: #000066 }
    :Link { font-family: Arial, Helvetica, sans-serif;
            color: #000066;
            text-decoration: none }
    :Link:visited { font-family: Arial, Helvetica, sans-serif;
            color: #000066;
            text-decoration: none }
    :Link:hover { font-family: Arial, Helvetica, sans-serif;
            background: #FFFFCC;
            text-decoration: none }
   -->
  </STYLE>
 </HEAD>
 <BODY       BGCOLOR = "#CCCCFF">
  <TABLE       WIDTH = "100%"
              BORDER = "0"
         CELLSPACING = "0"
               CLASS = "Page">
   <TR       BGCOLOR = "#6699FF">
    <TD       NOWRAP
              HEIGHT = "26"
             COLSPAN = "3">
     <FONT      SIZE = "+2"
               CLASS = "Page">CDR Advanced Search</FONT>
    </TD>
   </TR>
   <TR       BGCOLOR = "#FFFFCC">
    <TD       NOWRAP
             COLSPAN = "3">
     <SPAN     CLASS = "Page">
      <FONT     SIZE = "+1">Choose a document type</FONT>
     </SPAN>
    </TD>
   </TR>
   <TR>
    <TD       NOWRAP
             COLSPAN = "3"
              HEIGHT = "20">&nbsp;</TD>
   </TR>
   <TR>
    <TD       NOWRAP
             COLSPAN = "3"
               CLASS = "Page">
     <FONT     COLOR = "#000000">Select a document type to search:</FONT>
    </TD>
   </TR>
   <!--
   <TR>
    <TD       NOWRAP
             COLSPAN = "3"
               CLASS = "Page">&nbsp;</TD>
   </TR>
   -->
  </TABLE>
"""

menu    = """\
   <UL>
    <SPAN CLASS='Page'>
    <LI><A HREF='%s/CiteSearch.py%s'>Citation</A></LI>
    <LI><A HREF='%s/CountrySearch.py%s'>Country</A></LI>
    <LI><A HREF='%s/DISSearch.py%s'>Drug Information Summary</A></LI>
    <LI><A HREF='%s/HelpSearch.py%s'>Documentation</A></LI>
    <LI><A HREF='%s/GlossaryTermSearch.py%s'>Glossary Term</A></LI>
    <LI><A HREF='%s/MiscSearch.py%s'>Miscellaneous</A></LI>
    <LI><A HREF='%s/MediaSearch.py%s'>Media</A></LI>
    <LI><A HREF='%s/OrgSearch2.py%s'>Organization</A></LI>
    <LI><A HREF='%s/PersonSearch.py%s'>Person</A></LI>
    <LI><A HREF='%s/PersonLocSearch.py%s'>Person (Locations in Result
                                                  Display)</A></LI>
    <LI><A HREF='%s/PoliticalSubUnitSearch.py%s'>Political SubUnit</A></LI>
    <LI><A HREF='%s/ProtSearch.py%s'>Protocol</A></LI>
    <LI><A HREF='%s/SummarySearch.py%s'>Summary</A></LI>
    <LI><A HREF='%s/TermSearch.py%s'>Term</A></LI>
    </SPAN>
   </OL>
""" % (cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session,
       cdrcgi.BASE, session)
cdrcgi.sendPage(header + menu + "</FORM></BODY></HTML>")
