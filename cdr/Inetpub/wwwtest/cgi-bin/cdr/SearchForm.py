fields = (('Citation Title',          'Title'),
          ('Authors',                 'Authors'),
          ('Source',                  'Source'),
          ('Publication Info',        'PubInfo'),
          ('PMID',                    'PMID'),
          ('Citation ID',             'CitationID'))
buttons = (('submit', 'SubmitButton', 'Search'),
           ('submit', 'HelpButton',   'Help'),
           ('reset',  'CancelButton', 'Clear'),
           ('submit', 'SearchPubMed', 'Search Pub Med'))
html = """\
<HTML>
 <HEAD>
  <TITLE>Citation Search Form</TITLE>
  <META         HTTP-EQUIV  = "Content-Type"
                CONTENT     = "text/html; charset=iso-8859-1">
  <STYLE        TYPE        = "text/css">
   <!--
    .Page { font-family: Arial, Helvietica, sans-serif; color: #000066 }
   -->
  </STYLE>
 </HEAD>
 <BODY          BGCOLOR     = "#CCCCFF">
  <FORM         METHOD      = "post"
                ACTION      = "/cgi-bin/CitationSearch.py"
                NAME        = "CitationSearch">
   <TABLE       WIDTH       = "100%"
                BORDER      = "0"
                CELLSPACING = "0">
    <TR         BGCOLOR     = "#6699FF">
     <TD        NOWRAP
                HEIGHT      = "26"
                COLSPAN     = "2">
      <FONT     SIZE        = "+2"
                CLASS       = "Page">CDR Advanced Search</FONT>
     </TD>
    </TR>
    <TR         BGCOLOR     = "#FFFFCC">
     <TD        NOWRAP
                COLSPAN     = "2">
      <FONT     SIZE        = "+1"
                CLASS       = "Page">Citation</FONT>
     </TD>
    <TR>
    <TR>
     <TD        NOWRAP
                COLSPAN     = "2">&nbsp;</TD>
    </TR>
"""
for field in fields:
    html += """\
    <TR>
     <TD        NOWRAP
                ALIGN       = "right"
                CLASS       = "Page">%s &nbsp; </TD>
     <TD        WIDTH       = "55%%"
                ALIGN       = "left">
      <INPUT    TYPE        = "text"
                NAME        = "%s"
                SIZE        = "60">
     </TD>
    </TR>
""" % field
html += """\
    <TR>
     <TD        NOWRAP
                WIDTH       = "15%"
                CLASS       = "Page"
                VALIGN      = "top"
                ALIGN       = "right">Search Connector &nbsp; </TD>
     <TD        WIDTH       = "30%"
                ALIGN       = "left">
      <SELECT   NAME        = "Boolean"
                SIZE        = "1">
       <OPTION  SELECTED>AND</OPTION>
       <OPTION>OR</OPTION>
      </SELECT>
     </TD>
    </TR>
    <TR>
     <TD        WIDTH       = "15%">&nbsp;</TD>
     <TD        WIDTH       = "55%">&nbsp;</TD>
    </TR>
   </TABLE>
   <TABLE       WIDTH       = "100%"
                BORDER      = "0">
    <TR>
     <TD        COLSPAN     = "2">&nbsp; </TD>
"""
for button in buttons:
    html += """\
     <TD        WIDTH       = "13%%"
                ALIGN       = "center">
      <INPUT    TYPE        = "%s"
                NAME        = "%s"
                VALUE       = "%s">
     </TD>
""" % button
html += """\
     <TD        WIDTH       = "33%">&nbsp;</TD>
    </TR>
   </TABLE>
   <BR>
"""
print html + """\
   <CENTER>
    <INPUT      TYPE        = "submit"
                NAME        = "ImportButton"
                VALUE       = "Import">
    &nbsp;PubMed Citation ID TO Import:&nbsp;&nbsp;
    <INPUT      NAME        = "ImportID">
   </CENTER>
  </FORM>
 </BODY>
</HTML>
"""
