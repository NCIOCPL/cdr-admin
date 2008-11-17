#----------------------------------------------------------------------
# coding=latin-1
#
# $Id: GlossaryConceptFull.py,v 1.4 2008-11-17 19:47:54 venglisc Exp $
#
# Glossary Term Concept report
# This report takes a concept and displays all of the Term Name 
# definitions that are linked to this concept document
#
# $Log: not supported by cvs2svn $
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
          'RelatedExternalRef'    :'Related External Ref',
          'RelatedDrugSummaryRef' :'Related Drug Summary Ref',
          'RelatedSummaryRef'     :'Related Summary Ref',
          'StatusDate'            :'Status Date',
          'TermType'              :'Term Type',
          'TranslatedStatus'      :'Translated Status',
          'TranslationResource'   :'Translation Resource' }


#----------------------------------------------------------------------
# Dynamically create the title of the menu section 
#----------------------------------------------------------------------
def getSectionTitle(repType):
    if not repType:
        return "Glossary QC Report - Full"
    else:
        return "QC Report (Unrecognized Type)"


#----------------------------------------------------------------------
# More than one matching title; let the user choose one.
#----------------------------------------------------------------------
def showTitleChoices(choices):
    form = """\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += """\
   <INPUT TYPE='radio' NAME='DocId' VALUE='CDR%010d'>[CDR%d] %s<BR>
""" % (choice[0], choice[0], cgi.escape(choice[1]))
    cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, docType or '', repType or ''))
                    

#----------------------------------------------------------------------
# Create a single row to be displayed in an HTML table (two columns)
#----------------------------------------------------------------------
def addSingleRow(data, label):
    # Adding row for Date Last Reviewed 
    if data.has_key(label):
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
     <img src="http://bach.nci.nih.gov/cgi-bin/cdr/GetCdrImage.py?id=%s-300.jpg">
    </td>
   </tr>
""" % (LABEL[label], mediaValue, mediaID)
    
    return htmlRow

#----------------------------------------------------------------------
# Same as addSingleRow() but the label is only displayed for the first
# row.
#----------------------------------------------------------------------
def addMultipleRow(data, label):
    # Adding row for Date Last Reviewed 
    if data.has_key(label):
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
     tmpdoc += u" <TermNameString>" + \
               termData.get(language, u"@S@%s (en inglés)@E@" % termData['en'])\
                  + u"</TermNameString>\n"
     #tmpdoc += u" <TermNameString>" + \
     #          termData.get(language, "*** No '%s' definition ***" % language)\
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

     #doc = cdrcgi.decode(doc)
     #doc = re.sub("@@DOCID@@", docId, doc)

     return doc


#-----------------------------------------------------------------------
# Module to create a small XML snippet that can be submitted to a filter
# in order to substitute the PlaceHolder elements with the appropriate
# text from the ReplacementText elements.
#-----------------------------------------------------------------------
def displayComment(commentList):
     # Create the Glossary Definition
     tmpdoc  = u"\n<GlossaryTermDef xmlns:cdr = 'cips.nci.nih.gov/cdr'>\n"  

     # Add the CommentText and attributes
     for comment in commentList:
         tmpdoc += u"  %s\n" % comment

     tmpdoc += u"</GlossaryTermDef>\n"

     # Need to encode the unicode string to UTF-8 since that's what the 
     # filter module expects.  Decoding it back to unicode once the 
     # filtered document comes back.
     # --------------------------------------------------------------------
     doc = cdr.filterDoc('guest', ['name:Glossary Term Definition Update'], 
                         doc = tmpdoc.encode('utf-8'))

     #cdrcgi.bail(doc[0])
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
title    = "CDR Administration"
repType  = fields.getvalue("ReportType") or None
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, getSectionTitle(repType),
                         "GlossaryConceptFull.py", buttons, method = 'GET')
docId    = fields.getvalue("DocId")      or None
docType  = fields.getvalue("DocType")    or None
docTitle = fields.getvalue("DocTitle")   or None
version  = fields.getvalue("DocVersion") or None

if docId:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

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
# If we have a document type but no doc ID or title, ask for the title.
#----------------------------------------------------------------------
if not docId and not docTitle:
    extra = ""
    extra += "<INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>" % docType
    label = ['Glossary Title',
              'Glossary CDR ID']

    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  %s
  <TABLE>
   <TR>
    <TD ALIGN='right'><B>%s:&nbsp;</B><BR/>(use %% as wildcard)</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
   </TR>
   <TR>
    <TD> </TD>
    <TD>... or ...</TD>
   </TR>
   <TR>
    <TD ALIGN='right'><B>%s:&nbsp;</B></TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session, extra, label[0], label[1])
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
def getAllTermNames(docId, docType = 'GlossaryTermConcept'):
    try:
        query = """\
          SELECT qt.doc_id, dt1.name, qt.int_val, dt.name,
                 d1.active_status
            FROM query_term qt
            JOIN document d
              ON d.id = qt.int_val
            join doc_type dt
              on d.doc_type = dt.id
            JOIN document d1
              ON d1.id = qt.doc_id
            JOIN doc_type dt1
              ON d1.doc_type = dt1.id
           WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
             AND dt1.name = 'GlossaryTermName'
             AND dt.name  = 'GlossaryTermConcept'
             AND qt.int_val = """
        if docType == 'GlossaryTermConcept':
            query += '%s' % docId
        else:
            query += """\
               (SELECT int_val
                  FROM query_term
                 WHERE doc_id = %s
                   AND path = '/GlossaryTermName' + 
                              '/GlossaryTermConcept/@cdr:ref')""" % docId

        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with title '%s'" % docTitle)
        
        allTermNames = {}
        termNameIds = []
        
        for row in rows:
            termNameIds.append(row[0])

        allTermNames[row[1]] = termNameIds
        allTermNames[row[3]] = row[2]

    except cdrdb.Error, info:
        cdrcgi.bail('Failure selecting term names: %s' % info[1][0])

    return allTermNames



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
                          'NCIThesaurusID', 'RelatedDrugSummaryRef',
                          'RelatedExternalRef', 'RelatedSummaryRef']
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
                    if child.nodeName == 'RelatedDrugSummaryRef':
                        sharedContent['RelatedDrugSummaryRef'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:href').strip()])
                    if child.nodeName == 'RelatedExternalRef':
                        sharedContent['RelatedExternalRef'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:xref').strip()])
                    if child.nodeName == 'RelatedSummaryRef':
                        #cdrcgi.bail(child.getAttribute('cdr:href'))
                        sharedContent['RelatedSummaryRef'].append(
                                      [cdr.getTextContent(child).strip(),
                                       child.getAttribute('cdr:href').strip()])

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
                    #     {'DefinitionText':definition.toxml()})

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
                            if child.previousSibling.nodeName != gcList:
                                # Comments and ReplacementText contain
                                # attributes that need to be preserved.
                                # -------------------------------------
                                if gcList in ['ReplacementText', 'Comment']:
                                    rText = child
                                    concept['%s-%s' % (language, audience)
                                              ].update({gcList:[rText.toxml()]})
                                else:
                                    concept['%s-%s' % (language, audience)
                                              ].update({gcList:[
                                          cdr.getTextContent(child).strip()]})
                            else:
                                if gcList in ['ReplacementText', 'Comment']:
                                    rText = child
                                    concept['%s-%s' % (language, audience)][
                                          gcList].append(rText.toxml())
                                else:
                                    concept['%s-%s' % (language, audience)][
                                          gcList].append(
                                          cdr.getTextContent(child).strip())

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
                # ------------------------------------------------
                if not alternate:
                    for child in node.childNodes:
                        if child.nodeName == 'TermNameString':
                            termName[docId].update(
                               {language:cgi.escape(
                                         cdr.getTextContent(child).strip())})
                else:
                    for child in node.childNodes:
                        if child.nodeName == 'TermNameString':
                            if termName[docId].has_key(language + 'x'):
                                termName[docId][language + 'x'].append(
                                             cdr.getTextContent(child).strip())
                            else:
                                termName[docId].update(
                                          {language + 'x':
                                          [cdr.getTextContent(child).strip()]})

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
# If we have a document title but not a document ID, find the ID.
#----------------------------------------------------------------------
if docTitle and not docId:
    try:
        cursor.execute("""\
            SELECT d.id, d.title, dt.name
              FROM document d
              JOIN doc_type dt
                ON dt.id = d.doc_type
             WHERE dt.name in ('GlossaryTermName', 'GlossaryTermConcept')
               AND d.title LIKE ?""", (docTitle + '%'))
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with title '%s'" % docTitle)
        if len(rows) > 1:
            showTitleChoices(rows)
        intId   = rows[0][0]
        docId   = "CDR%010d" % intId
        docType = rows[0][2]
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up document title: %s' % info[1][0])

# ---------------------------------------------------------------------
# If we have a document ID but not a title find the docType
# ---------------------------------------------------------------------
if docId:
   try:
        cursor.execute("""\
            SELECT d.id, d.title, dt.name
              FROM document d
              JOIN doc_type dt
                ON dt.id = d.doc_type
             WHERE d.id = ?""", (intId))
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find CDR-ID '%s'" % docId)
        if len(rows) > 1:
            showTitleChoices(rows)
        intId   = rows[0][0]
        docId   = "CDR%010d" % intId
        docType = rows[0][2]
   except cdrdb.Error, info:
       cdrcgi.bail('Failure looking up CDR-ID: %s' % info[1][0])

# ---------------------------------------------------------------------
# If we have a GlossaryTermConcept document select all GTName documents
# linking to this concept.
# If we have a GlossaryTermName document find the concept and then the
# all of the other GTName documents linking to this concept.
# Either way we will end up with a concept document and all term name
# documents
# ---------------------------------------------------------------------
termNames = getAllTermNames(intId, docType)
# cdrcgi.bail(termNames)

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
""" % (intId, time.strftime(time.ctime()))
  
# Display the CDR-ID
# ------------------
html += '  <span class="big">CDR%s</span>' % intId

# Get the concept information to be displayed 
# -----------------------------------------------------------
conceptInfo = getConcept(termNames['GlossaryTermConcept'])

# We need to mark the term names that have been blocked.  For 
# this we need to go back to the database, which could have
# been done more intelligently, but the request to display
# blocked GTNs came after the program was nearly completed.
# -----------------------------------------------------------
termNameStatus = getTermNameStatus(termNames['GlossaryTermName'])
#cdrcgi.bail(termNames)

# Get the term name (for spanish and english) for each of the 
# related GlossaryTermName document and create a dictionary
# holding all of this information
# -----------------------------------------------------------
allTermsInfo = {}
for termId in termNames['GlossaryTermName']:
    termInfo = getNameDefinition(termId)
    allTermsInfo.update(termInfo)

# cdrcgi.bail(allTermsInfo)
# -----------------------------------------------------------------
# Display the GlossaryTermName Information
# -----------------------------------------------------------------
pattern   = re.compile("@@(.)@@")

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

#cdrcgi.bail(allTermsInfo)
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
    <td width="70%%">%s (CDR%s)""" % (termData[lang], id)

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
                html += u"""\
    <td width="70%%">
     <span class='special'>%s (en inglés)</span> (CDR%s)""" % (
                                                        termData['en'], id)

            # Resolve the PlaceHolder elements and create an HTML
            # table row from the resulting data
            # (The HTML output is created in the filter)
            # ----------------------------------------------------
            if conceptInfo.has_key('%s-%s' % (lang, aud)):
                #cdrcgi.bail(termData)
                definitionRow = resolvePlaceHolder(lang, termData, 
                                            conceptInfo['%s-%s' % (lang, aud)])
                ### There may be a better way to do this substitution???
                ### ####################################################
                replaceList = re.findall('@@.@@', definitionRow)
                for text in replaceList:
                    definitionRow = definitionRow.replace(text, text.upper())
                definitionRow = definitionRow.replace('@@', '')

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
                commentRow = displayComment(
                            conceptInfo['%s-%s' % (lang, aud)]['Comment'])
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
        sharedXml  = getSharedInfo(termNames['GlossaryTermConcept'])
        mediaHtml = addMediaRow(sharedXml, 'MediaLink')

        html += """
  <p />
  <table border="0" width="100%%" cellspacing="0" cellpadding="0">
  %s
  </table>
""" % mediaHtml

# Create the table rows for the elements that include an attribute
# ----------------------------------------------------------------
relDSRHtml   = addAttributeRow(sharedXml, 'RelatedDrugSummaryRef', indent=True)
relSRHtml    = addAttributeRow(sharedXml, 'RelatedSummaryRef',     indent=True)
relERHtml    = addAttributeRow(sharedXml, 'RelatedExternalRef',    indent=True)
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
if relDSRHtml or relSRHtml or relERHtml:
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
  </table>
""" % (relDSRHtml, relSRHtml, relERHtml)

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
