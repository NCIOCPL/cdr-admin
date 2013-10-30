#----------------------------------------------------------------------
# coding=latin-1
#
# $Id$
#
# Glossary Term Concept report
# This report takes a concept and displays all of the Term Name
# definitions that are linked to this concept document
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2009/03/03 15:01:16  bkline
# Rewritten in response to request #4482.
#
# Revision 1.6  2009/01/07 15:43:31  venglisc
# Fixed so that a Spanish definition isn't being displayed if the document
# is blocked. (Bug 4425)
#
# Revision 1.5  2008/11/18 18:44:25  venglisc
# Added CSS for insertion/deletion markup. (Bug 4375)
#
# Revision 1.4  2008/11/17 19:47:54  venglisc
# Modified display of blocked and none-existing GlossaryTermNames. (Bug 3948)
#
# Revision 1.3  2008/10/27 16:32:32  venglisc
# Changing element names from Spanish... to Translated... (Bug 3948)
#
# Revision 1.2  2008/06/12 19:04:01  venglisc
# Final version of the Glossary Concept Full report. (Bug 3948)
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys, time, xml.dom.minidom

# Setting the labels used for each element displayed
# --------------------------------------------------
LABEL = { 'DateLastModified'      :'Date Last Modified',
          'DateLastReviewed'      :'Date Last Reviewed',
          'DefinitionResource'    :'Definition Resource',
          'DefinitionStatus'      :'Definition Status',
          'Dictionary'            :'Dictionary',
          'MediaLink'             :'Media Link',
          'NCIThesaurusID'        :'NCI Thesaurus ID',
          'PDQTerm'               :'PDQ Term',
          'RelatedExternalRef'    :'Rel External Ref',
          'RelatedDrugSummaryLink':'Rel Drug Summary Link',
          'RelatedSummaryRef'     :'Rel Summary Ref',
          'RelatedGlossaryTermNameLink':'Rel Glossary Term',
          'StatusDate'            :'Status Date',
          'TermType'              :'Term Type',
          'TranslatedStatus'      :'Translated Status',
          'TranslationResource'   :'Translation Resource' }

#----------------------------------------------------------------------
# More than one matching term name; let the user choose one.
#----------------------------------------------------------------------
def showTermNameChoices(choices):
    form = """\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += """\
   <INPUT TYPE='radio' NAME='DocId' VALUE='CDR%010d'>[CDR%d] %s<BR>
""" % (choice[0], choice[0], cgi.escape(choice[1]))
    cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session))

#----------------------------------------------------------------------
# Create a single row to be displayed in an HTML table (two columns)
#----------------------------------------------------------------------
def addSingleRow(data, label):
    # Adding row for Date Last Reviewed
    if label in data:
        htmlRow = """
   <tr>
    <td>
     <b>%s</b>
    </td>
    <td>%s</td>
   </tr>
""" % (LABEL[label], data[label])

    return htmlRow


#----------------------------------------------------------------------
# Create a single row for the Media link such that the media is being
# displayed.
# We're creating a small DOM that we can parse in order to extract the
# CDR-ID of the media document.
#----------------------------------------------------------------------
def addMediaRow(data, label):
    #cdrcgi.bail(data[label])
    url = cdr.h.makeCdrCgiUrl("PROD", "GetCdrImage.py?id")
    htmlRow = ''
    for row in data['MediaLink']:
        mediaString = '''
        <Root xmlns:cdr="cips.nci.nih.gov/cdr">
        %s
        </Root>''' % row
        dom = xml.dom.minidom.parseString(mediaString)
        docElem = dom.documentElement

        for node in docElem.childNodes:
            if node.nodeName == 'MediaLink':
                for child in node.childNodes:
                    if child.nodeName == 'MediaID':
                        mediaValue = str(cdr.getTextContent(child).strip())
                        mediaID = child.getAttribute('cdr:ref')
        dom.unlink()
        htmlRow += """
   <tr>
    <td width="30%%" valign="top">
     <b>%s</b>
    </td>
    <td width="70%%">%s  <br>
     <img src="%s=%s-300.jpg">
    </td>
   </tr>
""" % (LABEL[label], mediaValue, url, mediaID)

    return htmlRow

#----------------------------------------------------------------------
# Same as addSingleRow() but the label is only displayed for the first
# row.
#----------------------------------------------------------------------
def addMultipleRow(data, label):
    # Adding row for Date Last Reviewed
    if label in data:
        iRow = -1
        htmlRows = ""
        for value in data[label]:
            iRow += 1
            if iRow == 0:
                iLabel = LABEL[label]
            else:
                iLabel = ''
            htmlRows += """
   <tr>
    <td width="30%%">
     <b>%s</b>
    </td>
    <td width="70%%">%s</td>
   </tr>""" % (iLabel, value)

    return htmlRows


#----------------------------------------------------------------------
# Same as addMultipleRow() but we are also adding a single attribute
#----------------------------------------------------------------------
def addAttributeRow(data, label, indent = False):
    # Adding row for Date Last Reviewed
    if data.has_key(label):
        iRow = -1
        htmlRows = ""
        for value, attribute in data[label]:
            try:
                attrValue = ('<a href="/cgi-bin/cdr/QcReport.py?' +
                             'Session=guest&amp;DocId=%d">CDR%d</a>') % (
                                              cdr.exNormalize(attribute)[1],
                                              cdr.exNormalize(attribute)[1])
            except:
                attrValue = '<a href="%s">%s</a>' % (attribute, attribute)

            iRow += 1
            if iRow == 0:
                iLabel = LABEL[label]
            else:
                iLabel = ''
            if not indent:
                htmlRows += """
   <tr>
    <td width="30%%">
     <b>%s</b>
    </td>
    <td width="70%%">%s (%s)</td>
   </tr>""" % (iLabel, value, attrValue)
            else:
                htmlRows += """
   <tr>
    <td width="3%%"> </td>
    <td width="27%%">
     <b>%s</b>
    </td>
    <td width="70%%">%s (%s)</td>
   </tr>""" % (iLabel, value, attrValue)

    return htmlRows


#-----------------------------------------------------------------------
# Module to create a small XML snippet that can be submitted to a filter
# in order to substitute the PlaceHolder elements with the appropriate
# text from the ReplacementText elements.
#-----------------------------------------------------------------------
def resolvePlaceHolder(language, termData, definitionText):
     # Create the Glossary Definition
     tmpdoc  = u"\n<GlossaryTermDef xmlns:cdr = 'cips.nci.nih.gov/cdr'>\n"
     tmpdoc += termData.get(language, u"@S@%s (en inglés)@E@" % termData['en'])\
                  + u"\n"
     #tmpdoc += u" <TermNameString>" + \
     #         termData.get(language, u"@S@%s (en inglés)@E@" % termData['en'])\
     #             + u"</TermNameString>\n"
     tmpdoc += u" %s\n" % definitionText['DefinitionText']

     # Add the ReplacementText from the GlossaryTermName documents
     if termData.has_key('ReplacementText'):
         tmpdoc += u" <GlossaryTermPlaceHolder>\n"
         for gtText in termData['ReplacementText']:
             tmpdoc += u"  %s\n" % gtText
         tmpdoc += u" </GlossaryTermPlaceHolder>\n"

     # Add the ReplacementText from the GlossaryTermConcept document
     if definitionText.has_key('ReplacementText'):
         tmpdoc += u" <GlossaryConceptPlaceHolder>\n"
         for gcText in definitionText['ReplacementText']:
             tmpdoc += u"  %s\n" % gcText
         tmpdoc += u" </GlossaryConceptPlaceHolder>\n"

     tmpdoc += u"</GlossaryTermDef>\n"

     # Need to encode the unicode string to UTF-8 since that's what the
     # filter module expects.  Decoding it back to unicode once the
     # filtered document comes back.
     # --------------------------------------------------------------------
     doc = cdr.filterDoc('guest', ['name:Glossary Term Definition Update'],
                         doc = tmpdoc.encode('utf-8'))

     if type(doc) in (type(""), type(u"")):
         cdrcgi.bail(doc)
     if type(doc) == type(()):
         doc = doc[0].decode('utf-8')

     return doc


# #-----------------------------------------------------------------------
# # Module to create a small XML snippet that can be submitted to a filter
# # in order to substitute the PlaceHolder elements with the appropriate
# # text from the ReplacementText elements.
# #-----------------------------------------------------------------------
# def displayComment(commentList):
#      # Create the Glossary Definition
#      tmpdoc  = u"\n<GlossaryTermDef xmlns:cdr = 'cips.nci.nih.gov/cdr'>\n"
#
#      # Add the CommentText and attributes
#      for comment in commentList:
#          tmpdoc += u"  %s\n" % comment
#
#      tmpdoc += u"</GlossaryTermDef>\n"
#
#      # Need to encode the unicode string to UTF-8 since that's what the
#      # filter module expects.  Decoding it back to unicode once the
#      # filtered document comes back.
#      # --------------------------------------------------------------------
#      doc = cdr.filterDoc('guest', ['name:Glossary Term Definition Update'],
#                          doc = tmpdoc.encode('utf-8'))
#
#      if type(doc) in (type(""), type(u"")):
#          cdrcgi.bail(doc)
#      if type(doc) == type(()):
#          doc = doc[0].decode('utf-8')
#
#      return doc


#-----------------------------------------------------------------------
# Module to create a small XML snippet that can be submitted to a filter
# in order to substitute the PlaceHolder elements with the appropriate
# text from the ReplacementText elements.
#-----------------------------------------------------------------------
def displayMarkup(xmlString, element):
     # Create XML document to be filtered
     if element == 'TermName':
         tmpdoc  = u"\n<TermNameDef xmlns:cdr = 'cips.nci.nih.gov/cdr'>\n"
         tmpdoc += u"  %s\n" % xmlString
         tmpdoc += u"</TermNameDef>\n"
     elif element == 'Comment':
         tmpdoc  = u"\n<GlossaryTermDef xmlns:cdr = 'cips.nci.nih.gov/cdr'>\n"
         # Add the CommentText and attributes
         for comment in xmlString:
             tmpdoc += u"  %s\n" % comment
         tmpdoc += u"</GlossaryTermDef>\n"


     # Need to encode the unicode string to UTF-8 since that's what the
     # filter module expects.  Decoding it back to unicode once the
     # filtered document comes back.
     # --------------------------------------------------------------------
     doc = cdr.filterDoc('guest', ['name:Glossary Term Definition Update'],
                         doc = tmpdoc.encode('utf-8'))

     if type(doc) in (type(""), type(u"")):
         cdrcgi.bail(doc)
     if type(doc) == type(()):
         doc = doc[0].decode('utf-8')

     return doc


#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Glossary Concept Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
docId    = fields.getvalue("DocId")
termName = fields.getvalue("TermName")
title    = "CDR Administration"
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, "Glossary QC Report - Full",
                         "GlossaryConceptFull.py", buttons, method = 'GET')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we have no request yet, put up the form.
#----------------------------------------------------------------------
if not docId and not termName:
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <TABLE>
   <TR>
    <TD ALIGN='right'><B>Glossary Term Name:&nbsp;</B><BR />
    (use %% as wildcard)</TD>
    <TD><INPUT SIZE='60' NAME='TermName'></TD>
   </TR>
   <TR>
    <TD> </TD>
    <TD>... or ...</TD>
   </TR>
   <TR>
    <TD ALIGN='right'>
     <B>Glossary Term Name or Glossary Term Concept CDR ID:&nbsp;</B>
    </TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Passing a CDR-ID and the document type
# Returning a list with a concept ID and all linking term names
#----------------------------------------------------------------------
def getAllTermNames(conceptId):
    cursor.execute("""\
        SELECT DISTINCT doc_id
                   FROM query_term
                  WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
                    AND int_val = ?""", conceptId, timeout = 300)
    return [row[0] for row in cursor.fetchall()]

#----------------------------------------------------------------------
# Getting the status of the GlossaryTermNames so that we can
# identify blocked terms.
#----------------------------------------------------------------------
def getTermNameStatus(termList):
    termNameIds = ','.join("%s" % id for id in termList)

    try:
        cursor.execute("""SELECT id, active_status
                          FROM document
                         WHERE id in (%s)""" % termNameIds)
        rows = cursor.fetchall()

    except cdrdb.Error, info:
        cdrcgi.bail("Error selecting term name status: %s" % info[1][0])

    statusList = {}
    for id, status in rows:
        statusList[id] = str(status)

    return statusList


#----------------------------------------------------------------------
# Passing a CDR-ID
# This function returns an HTML snippet in case a MediaLink element
# exists that's being shared between English and Spanish definitions.
#----------------------------------------------------------------------
def getSharedInfo(docId):
    try:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        row = cursor.fetchone()
        dom = xml.dom.minidom.parseString(row[0].encode('utf-8'))
        docElem = dom.documentElement

        sharedElements = ['MediaLink', 'TermType', 'PDQTerm',
                          'NCIThesaurusID', 'RelatedDrugSummaryLink',
                          'RelatedExternalRef', 'RelatedSummaryRef',
                          'RelatedGlossaryTermNameLink']
        sharedContent = {}
        for sharedElement in sharedElements:
            sharedContent[sharedElement] = []

        #cdrcgi.bail(docElem.childNodes[2].childNodes[1].toxml())
        for node in docElem.childNodes:
            if node.nodeName == 'MediaLink':
                sharedContent['MediaLink'].append(node.toxml())
            if node.nodeName == 'TermType':
                sharedContent['TermType'].append(
                                       cdr.getTextContent(node).strip())

            # For related information we add a list [value, attribute]
            # for each entry resulting in
            #   {'RelatedExternalRef:[[val1, attr1], [val2, attr2], ...], ...}
            # ----------------------------------------------------------------
            if node.nodeName == 'RelatedInformation':
                for child in node.childNodes:
                    if child.nodeName == 'RelatedDrugSummaryLink':
                        sharedContent['RelatedDrugSummaryLink'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:ref').strip()])
                    if child.nodeName == 'RelatedExternalRef':
                        sharedContent['RelatedExternalRef'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:xref').strip()])
                    if child.nodeName == 'RelatedSummaryRef':
                        #cdrcgi.bail(child.getAttribute('cdr:href'))
                        sharedContent['RelatedSummaryRef'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:href').strip()])
                    if child.nodeName == 'RelatedGlossaryTermNameLink':
                        #cdrcgi.bail(child.getAttribute('cdr:href'))
                        sharedContent['RelatedGlossaryTermNameLink'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:ref').strip()])

            if node.nodeName == 'PDQTerm':
                sharedContent['PDQTerm'].append(
                                      [cdr.getTextContent(node).strip(),
                                       node.getAttribute('cdr:ref').strip()])
            if node.nodeName == 'NCIThesaurusID':
                sharedContent['NCIThesaurusID'].append(
                                       cdr.getTextContent(node).strip())

    except cdrdb.Error, info:
        cdrcgi.bail("Error extracting shared Info: %s" % info[1][0])

    #cdrcgi.bail(sharedContent)
    return sharedContent

#----------------------------------------------------------------------
# We're selecting the information from the GTC document to be
# combined with the information from the GTN document.
# The data is stored in a dictionary.
#----------------------------------------------------------------------
def getConcept(docId):
    debugCount = sNum = eNum = 0
    debugList = []
    try:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        row = cursor.fetchone()
        dom = xml.dom.minidom.parseString(row[0].encode('utf-8'))
        docElem = dom.documentElement

        concept = {}
        for node in docElem.childNodes:
            if node.nodeName == 'TermDefinition' or \
               node.nodeName == 'TranslatedTermDefinition':
                if node.nodeName == 'TermDefinition':
                    language = 'en'
                else:
                    language = 'es'
                # I need the audience value (as the dictionary index)
                for child in node.childNodes:
                    if child.nodeName == 'Audience':
                        audience = str(cdr.getTextContent(child).strip())

                # Prepare the dictionary that we add the data to
                # The format of the dictionary will be
                #    concept{'en-Patient':{element1:value,
                #                          element2:[value1, value2],}
                #            'en-HP'     :{element1:value,
                #                          element2:[value1, value2], ...}}
                concept.update({'%s-%s' % (language, audience):{}})

                eNum += 1
                sNum += 1
                for child in node.childNodes:
                    # Adding all values that are not multiply occuring
                    # Creating entry 'key':value
                    # -----------------------------------------------------
                    for element in ['DefinitionStatus',
                                    'StatusDate', 'DateLastReviewed',
                                    'DateLastModified', 'TranslatedStatus',
                                    'TranslatedStatusDate']:
                        if child.nodeName == element:
                            concept['%s-%s' % (language, audience)].update(
                              {element:str(cdr.getTextContent(child).strip())})

                    # We need to preserve the inline markup of the
                    # definition text.
                    # -----------------------------------------------------
                    if (child.nodeName == 'DefinitionText'):
                        definition = child
                        concept['%s-%s' % (language, audience)].update(
                          {child.nodeName:definition.toxml()})

                    # Same as above but the MediaLink element is multiply
                    # occurring.
                    # -----------------------------------------------------
                    if (child.nodeName == 'MediaLink'):
                        if child.previousSibling.nodeName != 'MediaLink':
                            definition = child
                            concept['%s-%s' % (language, audience)].update(
                              {child.nodeName:[definition.toxml()]})
                        else:
                            definition = child
                            concept['%s-%s' % (language, audience)][
                               'MediaLink'].append(definition.toxml())

                    # Adding all values that are multiply occuring
                    # Creating entry 'key':[listitem, listitem, ...]
                    # ----------------------------------------------------
                    for gcList in ['DefinitionResource', 'Dictionary',
                                   'ReplacementText', 'Comment',
                                   'TranslationResource']:
                        if child.nodeName == gcList:
                            if concept['%s-%s' % (language, audience)].has_key(
                                                                       gcList):
                                # Comments and ReplacementText contain
                                # attributes that need to be preserved.
                                # -------------------------------------
                                if gcList in ['ReplacementText', 'Comment']:
                                    rText = child
                                    concept['%s-%s' % (language, audience)][
                                          gcList].append(rText.toxml())
                                    #if sNum == 2: cdrcgi.bail(concept)
                                else:
                                    concept['%s-%s' % (language, audience)][
                                          gcList].append(
                                          cdr.getTextContent(child).strip())
                            else:
                                if gcList in ['ReplacementText', 'Comment']:
                                    rText = child
                                    concept['%s-%s' % (language, audience)
                                              ].update({gcList:[rText.toxml()]})
                                    #if eNum == 2: cdrcgi.bail(concept)
                                else:
                                    concept['%s-%s' % (language, audience)
                                              ].update({gcList:[
                                          cdr.getTextContent(child).strip()]})

        dom.unlink()

    except cdrdb.Error, info:
        cdrcgi.bail("Error extracting Concept: %s" % info[1][0])

    return concept

#----------------------------------------------------------------------
# Select the information of the GTN document to be combined with the
# information from the GTC document.  We need the term named and the
# ReplacementText elements.
#----------------------------------------------------------------------
def getNameDefinition(docId):
    """
    We are returning a dictionary with the following information
       {CDR-ID : [ {'en' : termName-en, 'es' : termName-es}] }
    """
    try:
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        row = cursor.fetchone()
        dom = xml.dom.minidom.parseString(row[0].encode('utf-8'))
        docElem = dom.documentElement
        termName = {}
        termName[docId] = {}
        i = -1
        for node in docElem.childNodes:
            if node.nodeName in ('TermName', 'TranslatedName'):
                i += 1
                language  = node.getAttribute('language') or 'en'
                alternate = node.getAttribute('NameType') or None

                # We need to find the primary translation string
                # and also store additional alternate strings to
                # be displayed together.  These are stored as
                # 'enx':[one, two], 'esx':[uno, duo], ...
                # Note:  We need to escape possible '&' characters
                #        in the TermNameString
                # New requirement:
                #        We need to preserve insertion/deletion
                #        markup.
                # ------------------------------------------------
                if not alternate:
                    for child in node.childNodes:
                        if child.nodeName == 'TermNameString':
                            termName[docId].update(
                               {language:child.toxml()})
                #              {language:cgi.escape(
                #                        cdr.getTextContent(child).strip())})
                else:
                    for child in node.childNodes:
                        if child.nodeName == 'TermNameString':
                            if termName[docId].has_key(language + 'x'):
                                termName[docId][language + 'x'].append(
                                             child.toxml())
                            #                cdr.getTextContent(child).strip())
                            else:
                                termName[docId].update(
                                          {language + 'x':
                                          [child.toxml()]})
                            #             [cdr.getTextContent(child).strip()]})

            if node.nodeName == 'ReplacementText':
                if termName[docId].has_key('ReplacementText'):
                    rText = node
                    termName[docId]['ReplacementText'].append(
                                                   rText.toxml())
                else:
                    rText = node
                    termName[docId].update(
                               {'ReplacementText':[rText.toxml()]})
        dom.unlink()

    except cdrdb.Error, info:
        cdrcgi.bail("Error extracting Term Name: %s" % info[1][0])

    return termName

#----------------------------------------------------------------------
# Document ID can be given for the concept or for one of its names.
#----------------------------------------------------------------------
if docId:
    intId = cdr.exNormalize(docId)[1]
    cursor.execute("""\
        SELECT t.name
          FROM document d
          JOIN doc_type t
            ON t.id = d.doc_type
         WHERE d.id = ?""", intId)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Unable to find document '%s'" % docId)
    docType = rows[0][0]
    if docType == 'GlossaryTermConcept':
        conceptId = intId
    elif docType == 'GlossaryTermName':
        cursor.execute("""\
            SELECT int_val
              FROM query_term
             WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
               AND doc_id = ?""", intId)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("GlossaryTermName document %s not associated with "
                        "any GlossaryTermConcept document" % docId)
        else:
            conceptId = rows[0][0]
    else:
        cdrcgi.bail("%s is a %s document" % (docId, docType))

#----------------------------------------------------------------------
# If we have a term name but not a document ID, find the ID.
#----------------------------------------------------------------------
else:
    cursor.execute("""\
        SELECT c.int_val, n.value
          FROM query_term n
          JOIN query_term c
            ON c.doc_id = n.doc_id
         WHERE n.path = '/GlossaryTermName/TermName/TermNameString'
           AND c.path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
           AND n.value LIKE ?""", termName)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("No term names match '%s'" % termName)
    if len(rows) > 1:
        showTermNameChoices(rows)
    conceptId = rows[0][0]

#----------------------------------------------------------------------
# At this point we have a glossary term concept ID.  Find all the names
# for this concept.
#----------------------------------------------------------------------
termNameIds = getAllTermNames(conceptId)

# -------------------------------------------------------------------
# Create the HTML header, style sheet, etc.
# -------------------------------------------------------------------
htmlConcept = ""
html = """\
<HTML>
 <HEAD>
  <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <TITLE>CDR%s: Glossary Term Concept - Full QC Report</TITLE>
  <STYLE type="text/css">
   body          { font-family: sans-serif; }
   .big          { font-size: 14pt;
                   font-weight: bold; }
   .center       { text-align: center; }
   .name         { color: blue;
                   font-weight: bold;
                   background-color: #EEEEEE; }
   .term-normal  { background-color: yellow; }
   .term-capped  { background-color: yellow; }
   .term-name    { color: blue;
                   font-weight: bold; }
   .term-concept { color: green;
                   font-weight: bold; }
   .term-error   { color: red;
                   font-weight: bold; }
   .blocked, .special
                 { color: red;
                   font-weight: bold; }
   .attribute    { font-weight: normal;
                   font-style: italic;
                   background-color: #FFFFFF; }
   .insertapproved { color: red; }
   .deleteapproved { text-decoration: line-through; }
  </STYLE>
 </HEAD>
 <BODY>
  <div class="center">
  <span class="big">
   Glossary Term Concept - Full<br>
   QC Report
  </span>
  <br>
  <b>
   %s
  </b>
  </div>
""" % (conceptId, time.strftime(time.ctime()))

# Display the CDR-ID
# ------------------
html += '  <span class="big">CDR%s</span>' % conceptId

# Get the concept information to be displayed
# -----------------------------------------------------------
conceptInfo = getConcept(conceptId)

# We need to mark the term names that have been blocked.  For
# this we need to go back to the database, which could have
# been done more intelligently, but the request to display
# blocked GTNs came after the program was nearly completed.
# -----------------------------------------------------------
termNameStatus = getTermNameStatus(termNameIds)
# cdrcgi.bail(termNameStatus)

# Get the term name (for spanish and english) for each of the
# related GlossaryTermName document and create a dictionary
# holding all of this information
# -----------------------------------------------------------
allTermsInfo = {}
for termNameId in termNameIds:
    termInfo = getNameDefinition(termNameId)
    allTermsInfo.update(termInfo)

#cdrcgi.bail(allTermsInfo)
# -----------------------------------------------------------------
# Display the GlossaryTermName Information
# -----------------------------------------------------------------
#pattern   = re.compile("@@(.)@@")

# If all options should need to be printed on the QC report here
# are the possible values
# --------------------------------------------------------------
languages = ['en', 'es']
audiences = ['Patient', 'Health professional']

# The users decided to only display those term blocks for which a
# definition exists.
# Creating the languages/audiences list from the conceptInfo keys
# ---------------------------------------------------------------
lang_aud  = conceptInfo.keys()
languages = []
audiences = []
for la in lang_aud:
    if la.split('-')[0] not in set(languages):
        languages.append(la.split('-')[0])
    if la.split('-')[1] not in set(audiences):
        audiences.append(la.split('-')[1])

sections  = {'en':'English', 'es':'Spanish'}

# cdrcgi.bail(allTermsInfo)
for lang in languages:
    for aud in audiences:
        if '%s-%s' % (lang, aud) not in lang_aud: continue
        html += """
  <br>
  <br>
  <br>
  <span class="big">%s - %s</span>
  <table border="1" width="100%%" cellspacing="0" cellpadding="0">
""" % (sections[lang], aud)

        # Adding Term Name and Term Definition for language/audience
        # ----------------------------------------------------------
        for id, termData in allTermsInfo.iteritems():
            # Only if there doesn't exists a translation for an English
            # term would the Spanish term be missing.  In this case
            # (the 'else' block) we'll display the English term instead
            # ---------------------------------------------------------
            if termData.has_key(lang):
                html += """\
   <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
   <tr class="name">
    <td width="30%%">Name</td>"""

                # Display the term names and add any existing alternate
                # term names that exist for the non-English language
                # -----------------------------------------------------
                if termNameStatus[id] == 'A':
                    html += """\
    <td width="70%%">%s (CDR%s)""" % (displayMarkup(termData[lang], 'TermName'),
                                                                          id)

                    if termData.has_key(lang + 'x'):
                        html += " &nbsp;[alternate: %s]" % (
                                ', '.join([x for x in termData[lang + 'x']]))

                    html += """</td>
   </tr>"""
                # Display the blocked term names in red and don't
                # bother displaying the term definition
                # -----------------------------------------------
                else:
                    html += """\
    <td class="blocked" width="70%%">BLOCKED - %s (CDR%s)</td>
   </tr>""" % (termData[lang], id)
                    continue

            else:
                html += """\
   <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
   <tr class="name">
    <td width="30%%">Name</td>"""

                # If there doesn't exist a Spanish name we'll still
                # have to check if the document might be blocked
                #   (termNameStatus[id] == 'I'
                # and suppress display of the definition, if it is.
                # --------------------------------------------------
                if termNameStatus[id] == 'A':
                    html += u"""\
    <td width="70%%">
     <span class='special'>%s (en inglés)</span> (CDR%s)""" % (
                                                        termData['en'], id)
                else:
                    html += u"""\
    <td class="blocked" width="70%%">BLOCKED -
     <span class='special'>%s (en inglés)</span> (CDR%s)""" % (
                                                        termData['en'], id)
                    continue

            # Resolve the PlaceHolder elements and create an HTML
            # table row from the resulting data
            # (The HTML output is created in the filter)
            # ----------------------------------------------------
            if conceptInfo.has_key('%s-%s' % (lang, aud)):
                definitionRow = resolvePlaceHolder(lang, termData,
                                            conceptInfo['%s-%s' % (lang, aud)])
                ### There may be a better way to do this substitution???
                ### ####################################################
                # If we have a CAPPEDTERMNAME PlaceHolder the filter has
                # enclosed the term with @@...@@ characters.  However, the
                # term name could be marked up with insertion/deletion
                # markup.  We need to find the first character within this
                # string that needs to be capitalized.
                # If the first character is a '<' this indicates the
                # beginning of the <span> element for markup. The first
                # character after the </span> should then be capitalized.
                # --------------------------------------------------------
                replaceList = re.findall('@@.*?@@', definitionRow)

                if replaceList:
                    for text in replaceList:
                        m1 = re.sub('@@', '', text)
                        m2 = re.sub('@@', '', m1)
                        if m2[0] == '<':
                            m3 = re.search('<.*?>.', m2)
                            rtext = m3.group(0)[:-1] + \
                                    m3.group(0)[-1].upper() + \
                                    re.sub(m3.group(0), '', m2)
                        else:
                            rtext = m2[0].upper() + m2[1:]
                        definitionRow = definitionRow.replace(text, rtext)

                # If there was a term without Spanish name display it
                # in red to stand out.
                # ----------------------------------------------------
                definitionRow = definitionRow.replace('@S@',
                                             '<span class="special">', 1)
                definitionRow = definitionRow.replace('@E@', '</span>')
                html += definitionRow

        html += """
  </table>
  <p/>
  <table border="0" width="100%%" cellspacing="0" cellpadding="0">"""

        # Adding the Term Concept information at the end of each
        # language/audience section
        # -----------------------------------------------------------
        if conceptInfo.has_key('%s-%s' % (lang, aud)):
            # Adding row for Definition Resource
            if conceptInfo['%s-%s' % (lang, aud)].has_key(
                                                      'DefinitionResource'):
                html += addMultipleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'DefinitionResource')

            # Adding row for Translation Resource
            if conceptInfo['%s-%s' % (lang, aud)].has_key(
                                                      'TranslationResource'):
                html += addMultipleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'TranslationResource')

            # Adding row for MediaLink
            if conceptInfo['%s-%s' % (lang, aud)].has_key('MediaLink'):
                #cdrcgi.bail(conceptInfo['%s-%s' % (lang, aud)]['MediaLink'])
                html += addMediaRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'MediaLink')
            # Adding row for Dictionary
            if conceptInfo['%s-%s' % (lang, aud)].has_key('Dictionary'):
                html += addMultipleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'Dictionary')

            # Adding row for Definition Status
            if conceptInfo['%s-%s' % (lang, aud)].has_key('DefinitionStatus'):
                html += addSingleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'DefinitionStatus')
            # Adding row for Definition Status
            if conceptInfo['%s-%s' % (lang, aud)].has_key('TranslatedStatus'):
                html += addSingleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'TranslatedStatus')
            # Adding row for Status Date
            if conceptInfo['%s-%s' % (lang, aud)].has_key('StatusDate'):
                html += addSingleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'StatusDate')

            # Adding Comment rows
            # We need to process the attributes, too, so we're sending
            # the Comment node through a filter
            if conceptInfo['%s-%s' % (lang, aud)].has_key('Comment'):
                commentRow = displayMarkup(
                            conceptInfo['%s-%s' % (lang, aud)]['Comment'],
                                                               'Comment')
                html += commentRow
            # Adding row for Date Last Modified
            if conceptInfo['%s-%s' % (lang, aud)].has_key('DateLastModified'):
                html += addSingleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'DateLastModified')
            # Adding row for Date Last Reviewed
            if conceptInfo['%s-%s' % (lang, aud)].has_key('DateLastReviewed'):
                html += addSingleRow(conceptInfo['%s-%s' % (lang, aud)],
                                    'DateLastReviewed')

        html += """
  </table>
"""
    if lang == 'en':
        sharedXml  = getSharedInfo(conceptId)
        mediaHtml = addMediaRow(sharedXml, 'MediaLink')

        html += """
  <p />
  <table border="0" width="100%%" cellspacing="0" cellpadding="0">
  %s
  </table>
""" % mediaHtml

# Create the table rows for the elements that include an attribute
# ----------------------------------------------------------------
relDSRHtml   = addAttributeRow(sharedXml, 'RelatedDrugSummaryLink', 
                                                                   indent=True)
relSRHtml    = addAttributeRow(sharedXml, 'RelatedSummaryRef',     indent=True)
relERHtml    = addAttributeRow(sharedXml, 'RelatedExternalRef',    indent=True)
relGLHtml    = addAttributeRow(sharedXml, 'RelatedGlossaryTermNameLink', 
                                                                   indent=True)
pdqTermHtml  = addAttributeRow(sharedXml, 'PDQTerm')

# Create the table rows for the elements without attribute
# --------------------------------------------------------
termTypeHtml = addMultipleRow(sharedXml, 'TermType')
nciThesHtml  = addMultipleRow(sharedXml, 'NCIThesaurusID')

# Adding Term information to HTML document
# ----------------------------------------
html += """
  <p />
  <table border="0" width="100%%" cellspacing="0" cellpadding="0">
  %s
  </table>
""" % (termTypeHtml)

# Adding the related information to HTML document
# -----------------------------------------------
if relDSRHtml or relSRHtml or relERHtml or relGLHtml:
    html += """
  <table border="0" width="100%%" cellspacing="0" cellpadding="0">
   <tr>
    <td colspan="2">
     <b>Related Information</b>
    </td>
   </tr>
  %s
  %s
  %s
  %s
  </table>
""" % (relDSRHtml, relSRHtml, relERHtml, relGLHtml)

# Adding PDQTerm and Thesaurus information to HTML document
# ---------------------------------------------------------
html += """
  <table border="0" width="100%%" cellspacing="0" cellpadding="0">
  %s
  %s
  </table>
""" % (pdqTermHtml, nciThesHtml)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
# Create the HTML footer
html += """
 </BODY>
</HTML>"""

cdrcgi.sendPage(html)
