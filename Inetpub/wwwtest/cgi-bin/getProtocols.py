#----------------------------------------------------------------------
# $Id: getProtocols.py,v 1.1 2005-06-29 16:14:14 bkline Exp $
#
# Test for AACI SOAP interface.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, xml.sax.saxutils

def fix(s):
    return xml.sax.saxutils.escape(s)

def protRow(p):
    url    = fix(p.prot_url)
    title  = fix(p.prot_title).replace(u";", "; ")
    status = fix(p.prot_accrual_status)
    num    = fix(p.prot_num)
    link   = u"<a href='%s'>%s</a>" % (url, num)
    return u"""\
    <tr>
     <td class='frmText' valign='top'>%s</td>
     <td class='frmText' valign='top'>%s</td>
     <td class='frmText' valign='top'>%s</td>
    </tr>""" % (link, title, status)

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
term      = fields and fields.getvalue('term') or None
termParam = term and xml.sax.saxutils.quoteattr(term) or ''
html      = [u"""\
<html>
 <head>
  <title>AACI Web Service - Test Interface</title>
  <style type='text/css'>
   body       { color: black; background-color: white;
                font-family: Verdana, Arial;
                margin-left: 0px; margin-top: 0px; }
   #content   { margin-left: 30px; font-size: .70em; padding-botton: 2em; }
   a:link     { color: #336699; font-weight: bold;
                text-decoration: underline; }
   a:visited  { color: #6699cc; font-weight: bold;
                text-decoration: underline; }
   a:active   { color: #336699; font-weight: bold;
                text-decoration: underline; }
   a:hover    { color: cc3300; font-weight: bold;
                text-decoration: underline; }
   p          { margin-top: 0px; margin-bottom: 12px; }
   pre        { background-color: #e5e5cc; padding: 5px;
                font-family: Courier New; font-size: x-small;
                margin-top: -5px; border: 1px #f0f0e0 solid; }
   td         { font-size: .7em; }
   h2         { font-size: 1.5em; font-weight: bold; margin-top: 25px;
                margin-bottom: 10px; border-top: 1px solid #003366;
                margin-left: -15px; color: #003366; }
   h3         { font-size: 1.1em; margin-left: -15px; margin-top: 10px;
                margin-bottom: 10px; }
   ul         { margin-top: 10px; margin-left: 20px; }
   ol         { margin-top: 10px; margin-left: 20px; }
   li         { margin-top: 10px; }
   font.value { color: darkblue; font: bold; }
   font.key   { color: darkgreen; font: bold; }
   .heading1  { color: #ffffff; font-family: Tahoma, Arial; font-size: 26px;
                font-weight: normal; background-color: #003366;
                margin-top: 0px; margin-bottom: 0px; margin-left: -30px;
                padding-top: 10px; padding-bottom: 3px; padding-left: 15px;
                width: 105%%; }
   .button    { background-color: #dcdcdc; font-family: Verdana, Arial;
                font-size: 1em; border-top: #cccccc 1px solid;
                border-bottom: #666666 1px solid;
                border-left: #cccccc 1px solid;
                border-right: #666666 1px solid; }
   .frmheader { color: black; background: #dcdcdc; font-family: Verdana, Arial;
                font-size: .7em; font-weight: normal;
                border-bottom: 1px solid #dcdcdc;
                padding-top: 2px; padding-bottom: 2px; }
   .frmtext   { font-family: Verdana, Arial; font-size: .7em;
                margin-top: 8px; margin-bottom: 0px; margin-left: 32px; }
   .frmInput  { font-family: Verdana, Arial; font-size: 1em; }
   .intro     { margin-left: -15px; }
  </style>
 </head>
 <body>
  <div id='content'>
   <p class='heading1'>AACIService</p><br>
   <h2>getProtocols</h2>
   <p class='intro'></p>
   <h3>Test</h3>
   To test the operation, click the 'Invoke' button.
   <form method='post'>
    <table cellspacing='0' cellpadding='4' frame='box' bordercolor='#dcdcdc'
           rules='none' style='border-collapse: collapse;'>
     <tr>
      <td class='frmHeader' background='#dcdcdc'
          style='border-right: 2px solid white'>Parameter</td>
      <td class='frmHeader' background='#dcdcdc'>Value</td>
     </tr>
     <tr>
      <td class='frmText' style='color: black; font-weight:normal;'
       >SearchString</td>
      <td><input class='frmInput' size='50' name='term' value=%s></td>
     </tr>
     <tr>
      <td colspan='2' align='right'><input type='submit'
                                           value='Invoke' class='button'></td>
     </tr>
    </table>
   </form>
   <br>""" % termParam]
if term:
    import SOAPpy
    url    = u'http://bach.nci.nih.gov/cgi-bin/aaciservice.py'
    proxy  = SOAPpy.WSDL.SOAPProxy(url)
    result = proxy.getProtocols(SearchString = term)
    prots  = type(result) not in (str, unicode) and result.Protocol or []
    prots  = type(prots) not in (list, tuple) and [prots] or prots
    #nProts = type(result) not in (str, unicode) and len(result.Protocol) or 0
    #if nProts and type(result.Protocol) != list:
    #    nProts = 1
    html.append(u"""\
   <h2>Search Results (%d Protocols)</h2><br>""" % len(prots))
    html.append(u"""\
   <table cellspacing='0' cellpadding='4' frame='box' bordercolor='#dcdcdc'
          rules='none' style='border-collapse: collapse;' width='100%'>
    <tr>
     <td class='frmHeader' background='#dcdcdc' width='20%'
         style='border-right: 2px solid white' valign='top'><b>Protocol
         Number</b></td>
     <td class='frmHeader' background='#dcdcdc' width='65%'
         style='border-right: 2px solid white' valign='top'><b>Protocol
         Title</b></td>
     <td class='frmHeader' background='#dcdcdc' valign='top'><b>Protocol
         Status</b></td>
    </tr>""")
    #if nProts == 1:
    #    html.append(protRow(result.Protocol))
    #elif nProts > 1:
    #    for p in result.Protocol:
    #        html.append(protRow(p))
    for p in prots:
        html.append(protRow(p))
    html.append("""\
   </title>""")
    
html.append(u"""\
  </span>
 </body>
</html>""")
cdrcgi.sendPage(u"\n".join(html))
