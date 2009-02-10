#----------------------------------------------------------------------
#
# $Id: CGGlossifierTest.py,v 1.3 2009-02-10 19:32:28 bkline Exp $
#
# Minimal test interface for periodically checking to make sure no
# bit rot has set in while we're waiting for the Cancer.gov team
# to QC the service.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2008/12/18 15:55:42  bkline
# Code and CSS cleanup.
#
# Revision 1.1  2008/12/11 13:15:41  bkline
# Unit test for glossifier service built for Cancer.gov.
#
#----------------------------------------------------------------------
import warnings, cgi, cdrcgi, re

# Suppress deprecation warnings: they break CGI responses.
warnings.simplefilter('ignore')
from SOAPpy import WSDL
from Glossifier_client import *

class Term:
    def __init__(self, docId, start, length, lang, first, dictionary):
        self.docId = int(re.sub(u"[^\\d+]", u"", docId))
        self.start = int(start)
        self.length = int(length)
        self.lang = lang
        self.first = first and first not in ('false', 'False', '0')
        self.dictionary = dictionary
        self.string = u""

def markUpFragment(fragment, languages, dictionaries, api):
    terms = []
    if api == 'SOAPpy':
        server = WSDL.Proxy('http://PDQUpdate.cancer.gov/u/glossify')
        response = server.glossify(fragment, dictionaries, languages)
        if not response or type(response) is str:
            terms = []
        elif type(response.Term) is list:
            for t in response.Term:
                term = Term(t.docId, t.start, t.length, t.language,
                            t.firstOccurrence, t.dictionary)
                terms.append(term)
        else:
            t = response.Term
            term = Term(t.docId, t.start, t.length, t.language,
                        t.firstOccurrence, t.dictionary)
            terms = [term]
            
    else:
        loc = GlossifierLocator()
        port = loc.getGlossifierSoap()
        request = glossifySoapIn()
        request._fragment = fragment
        request._languages = request.new_languages()
        request._languages._string = languages
        request._dictionaries = request.new_dictionaries()
        request._dictionaries._string = dictionaries
        response = port.glossify(request)
        for t in response.GlossifyResult.Term:
            term = Term(t._docId, t._start, t._length, t._language,
                        t._firstOccurrence, t._dictionary)
            terms.append(term)
    segments = []
    pos = 0
    langMap = { u'en': u'English', u'es': u'Spanish' }
    pattern = (u'http://www.cancer.gov/Common/PopUps/popDefinition.aspx?'
               u'id=%d&version=Patient&language=%s')
    for t in terms:
        if t.first and t.start >= pos:
            nextPos = t.start + t.length
            if t.start > pos:
                segments.append(fragment[pos:t.start])
                phrase = cgi.escape(fragment[t.start:nextPos])
                lang = langMap.get(t.lang, 'English')
                url = pattern % (t.docId, lang)
                repl = (u"<a target='_blank' href='%s'>%s</a>" % (url, phrase))
                segments.append(repl)
                pos = nextPos
    if pos < len(fragment):
        segments.append(fragment[pos:])
    fragment = u"".join(segments)
    return u"Marked Up Fragment:<br /><div id='result'>%s</div>" % fragment

fields = cgi.FieldStorage()
fragment = (fields.getvalue('fragment') or u"").decode('utf-8')
languages = fields.getlist('languages')
dictionaries = fields.getlist('dictionaries')
api = fields.getvalue('api')
if fragment:
    markedUpFragment = markUpFragment(fragment, languages, dictionaries, api)
else:
    markedUpFragment = u""
    fragment = (u"<p>Gerota\u2019s capsule breast cancer and mammography "
                u"as well as invasive breast cancer, too.  And here's "
                u"another breast cancer which shouldn't be glossified.  "
                u"This occurrence of {{surgery}} should also be skipped, "
                u"and this <a href='javascript:skipMe()'>surgery</a>, which "
                u"already has link markup, should not be re-glossified.  "
                u"This SuRgErY, on the other hand, is OK!</p>")
html = u"""\
<html>
 <head>
  <title>Cancer.gov Glossifier Tester</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1 { font-size: 14pt; color: maroon; }
   th { width: 200px; text-align: right; padding-right: 10px; }
   #result { border: 2px solid green; padding: 5px; margin-right: 100px; }
   textarea { height: 300px; width: 800px; border: none; }
   form fieldset { border: green 1px solid; padding: 10px;
                   margin: 5px 0 15px; width: 500px; }
   form fieldset legend { fontsize: 1.1em; color: green; }
  </style>
 </head>
 <body>
  <h1>Cancer.gov Glossifier Tester</h1>
  <form method='POST' action='CGGlossifierTest.py'>
   <fieldset>
    <legend>Control Parameters</legend>
    <table>
     <tr>
      <th>Limit to Dictionaries:</th>
      <td>
       <input type='checkbox' name='dictionaries' value='Cancer.gov' />
       Cancer.gov<br />
      </td>
     </tr>
     <tr>
      <th>Limit to Languages:</th>
      <td>
       <input type='checkbox' name='languages' value='en' />
       English &nbsp; &nbsp;
       <input type='checkbox' name='languages' value='es' />
       Spanish
      </td>
     </tr>
     <tr>
      <th>Package to Use:</th>
      <td>
       <input type='radio' name='api' value='SOAPpy' />
       SOAPpy &nbsp; &nbsp;
       <input type='radio' name='api' value='ZSI' CHECKED />
       ZSI
      </td>
     </tr>
    </table>
   </fieldset>
   <fieldset>
    <legend>Input Fragment</legend>
    <textarea name='fragment'>%s</textarea>
   </fieldset>
   <input type='submit' value='Submit Request' />
   <br /><br />
   %s
  </form>
 </body>
</html>""" % (cgi.escape(fragment), markedUpFragment)
print "Content-type: text/html; charset=utf-8\n"
print html.encode('utf-8')
