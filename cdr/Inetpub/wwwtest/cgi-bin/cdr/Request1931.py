#----------------------------------------------------------------------
# Attempt to guess at the expected enrollment for an InScopeProtocol
# based on the text content of the ProjectedAccrual element.
#
# The program uses regular expressions, tricks and heuristics
# to make a guess.  If it is able to guess something, it tells a user
# what it guessed and allows a user to accept or override the guess,
# or to enter a new value from scratch where the program could not
# guess.
#
# The text values are very often not straightforwardly interpretable
# by any practical to produce program.  Therefore, use this with care!
#
# It is intended that the program will be used to populate initial
# values of existing protocols, and then never used again.
#
# The program is invoked in up to three stages:
#
#    1. Ask the user how many docs to process.  The user should not
#       try to process more than he can review in one sitting.
#
#    2. Display results to the user.
#
#    3. Allow the user to submit the results, plus any overrides for
#       permanent update.
#
# $Id: Request1931.py,v 1.4 2006-03-16 21:59:42 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2006/01/26 22:00:23  ameyer
# Suppressed ModifyDocs output to stderr.
# Fixed button bug - no navigation for "Exit" button.
#
# Revision 1.2  2006/01/19 23:56:09  ameyer
# Replaced a generator function "return (row[0] for row in rows" with
# code to make the program backwards compatible with the version of
# Python on Bach.
#
# Revision 1.1  2006/01/04 03:28:07  ameyer
# Add ExpectedEnrollment elements.
#
#----------------------------------------------------------------------

import re, cgi, xml.dom.minidom, cdr, cdrdb, cdrcgi, ModifyDocs

# For screen headers
TITLE   = "Estimate ExpectedEnrollment"
SCRIPT  = "Request1931.py"
ADMIN   = "Admin menu"
BUTTONS = ["Submit Request", ADMIN]

# Display this if no key element found
NO_ACCRUAL_TEXT = "No ProjectedAccrual element found."

#----------------------------------------------------------------------
# Class for performing regular expressions on accrual text
#----------------------------------------------------------------------
class AccPat:

    # Fixed literal number patterns
    # Number with optional comma and optional range, e.g.,
    #   40
    #   40-50
    #   1,400
    #   1,100-1,200"
    __nChk  = r"(\d+(,\d+)?\-)?(?P<n>\d+(,\d+)?)"
    __comma = re.compile(",")
    __atPat = re.compile("@@")

    def __init__(self, name, pattern):
        """
        Constructor

        Pass:
            name    - For display to user if there's a match.
            pattern - Regular expression, must include string "@@" in the
                      place to look for enrollment numbers.
        """
        self.__name = name

        # Insert pattern to look for digits with optional commas
        atPat = AccPat.__atPat.sub(AccPat.__nChk, pattern)

        # And compile the pattern
        self.__pat  = re.compile(atPat)

    def run(self, accText, accNum):
        """
        Check accrual text.

        Pass:
            accText - Text to process.
            accNum  - Our current guess as to its value.
                      Should be zero for first call.

        Return:
            Tuple of:
                pattern name
                generated number
        """
        for match in self.__pat.finditer(accText):
            # Find and convert number string with possible comma
            num = int(AccPat.__comma.sub("", match.group('n')))

            # Pick largest we found
            if num > accNum:
                accNum = num

        return (self.__name, accNum)

#----------------------------------------------------------------------
# Filter and Transform classes for ModifyDocs.Job object.
# It will invoke these to find and modify all docs, using standard
#   techniques for versioning and processing of publishable versions.
#----------------------------------------------------------------------
class Filter:
    def getDocIds(self):
        """
        Get doc ids and matching ExpectedEnrollment numbers from
        the user input form.

        Creates the global dictionary "idVals" that can be looked at
        by the Transform.run() function.
        """
        global fields, idVals

        # Begin by processing the form data to extract docIds and values
        i = 0
        while True:
            # Get docIds, in sequence
            docIdStr  = fields.getvalue('docId%d' % i) or None
            if not docIdStr:
                # No more
                break
            valStr    = fields.getvalue('docVal%d'% i) or None
            usrValStr = fields.getvalue('docUsrVal%d' % i) or None

            # String to int
            docId  = int(docIdStr)
            val    = valStr and int(valStr) or 0
            usrVal = usrValStr and int(usrValStr) or 0

            # Substitute usrVal for val, if it exists
            if usrVal:
                val = usrVal

            # If we have a value, save doc Id and values as a pair
            # User can effectively delete a value by using zero
            if (val):
                idVals[docId] = val

            # Next form variable set
            i += 1

        # Return all the doc ids to caller
        idList = idVals.keys()
        idList.sort()
        return idList

class Transform:

    def __init__(self):
        # xslt filter to update document
        self.__filter="""\
<?xml version="1.0"?>
<!-- ===============================================================
 Add ExpectedEnrollment element to InScopeProtocols.
================================================================ -->
<xsl:transform       xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                     xmlns:cdr = "cips.nci.nih.gov/cdr"
                       version = "1.0">

 <xsl:output            method = "xml"/>
 <!-- ===============================================================
 Passed parameters:
    $enroll = Enrollment.
 ================================================================ -->
 <xsl:param               name = "enroll"/>

 <!-- ===============================================================
 Default rule, copy all document elements to output.
 ================================================================ -->
 <xsl:template           match = "@*|comment()|*|
                                   processing-instruction()|text()">
  <xsl:copy>
   <xsl:apply-templates select = "@*|comment()|*|
                                   processing-instruction()|text()"/>
  </xsl:copy>
 </xsl:template>

 <!-- ===============================================================
 Add the enrollment after ProtocolPhase.
 ================================================================ -->
 <xsl:template           match ='/InScopeProtocol/ProtocolPhase'>
   <!-- Copy the phase -->
   <xsl:copy-of         select = "."/>

   <!-- Add the ExpectedEnrollment -->
   <xsl:element           name = 'ExpectedEnrollment'>
     <xsl:value-of      select = '$enroll'/>
   </xsl:element>
 </xsl:template>
</xsl:transform>
"""
    def run(self, docObj):
        """
        Filter the document using the enrollment value placed into
        a global by the Filter.getDocIds() generator.

        Pass:
            docObj - cdr.Doc document object.
        """
        global idVals

        # Get ExpectedEnrollment parameter from global
        docId = cdr.exNormalize(docObj.id)[1]
        parms = (('enroll', str(idVals[docId])),)

        # Filter doc, adding ExpectedEnrollment
        response = cdr.filterDoc('guest', self.__filter,
                                 doc=docObj.xml, inline=1, parm=parms)
        if type(response) in (type(""), type(u"")):
            raise Exception("Failure filtering document: %s" % response)

        return response[0]

def createForm1(session):
    """
    Generate the form that asks for how many docs to scan.

    Pass:
        session - Session identifier.

    Return:
        Form, as html string.
    """
    global TITLE, SCRIPT, BUTTONS

    section = "Enter the number of enrollment estimates you'd like to see"
    html    = cdrcgi.header(TITLE, TITLE, section, SCRIPT, BUTTONS) + \
"""
<p>This program will read some number of InScopeProtocols that have
IDType="ClinicalTrials.gov ID" and which do not yet have an
ExpectedEnrollment element.  For each one, it will scan any text
in the ProjectedAccrual element and attempt to match various patterns
that might possibly reveal the expected enrollment.<p>

<p>The inferred values will be presented to you in a web form, with
the associated text from which the values were inferred.  You may
then accept the inferred values, or override any particular ones,
and then Submit the changes.  The program will update the actual
protocol documents, inserting the ExpectedEnrollment elements.<p>

<p>You will also be able to Cancel processing, with no database updates.</p>

<p>Enter the number of documents to process.  You should pick a number
no larger than the number you are sure you can comfortably review at
one sitting, e.g., 25, 50, or whatever</p>

<input type='hidden' name='formNum' value='form1' />
<input type='hidden' name='%s' value='%s' />
<p><strong>Number of protocols to process: </strong>
   <input type='text' name='numDocs' size='6' /></p>

</FORM>
</BODY>
</HTML>
""" % (cdrcgi.SESSION, session)

    return html

def createForm2(session, docIds):
    """
    Generate the form that asks for how many docs to scan.

    Pass:
        session - Session identifier.
        docIds  - Sequence (or generator thereof) of doc IDs.

    Return:
        Form, as html string.
    """
    global TITLE, SCRIPT, BUTTONS

    # Header and fixed text
    section = "Look at some wild guesses!"
    html    = cdrcgi.header(TITLE, TITLE, section, SCRIPT, BUTTONS) + \
"""
<p>For each protocol listed below, please read the text that was used
to generate an ExpectedEnrollment value and compare it to the value
generated by the program.  The text is shown without any XML tag
structure it had in the original document.</p>

<p>If the value is correct, do nothing.</p>

<p>If the value is incorrect and you wish to create a different
ExpectedEnrollment value, enter the new value in the input box
beside the generated value.</p>

<p>If the value is incorrect, but you do not want to create any
ExpectedEnrollment element in the protocol at all, enter 0 (numeric
zero) in the input box.  The document will then be skipped.  Skipped
documents will appear on subsequent runs of this program.</p>

<p>After reviewing and correcting all of the entries, click "Submit"
to cause all of the listed documents to be updated to include an
ExpectedEnrollment element with the generated or corrected value.</p>

<p>If the test mode box is checked, updates will be written to the
file system using the global change test mode mechanism.</p>

<p>If test mode is unchecked, the database will be updated.</p>

<center><strong>Test mode: </strong>
        <input type='checkbox' name='testMode' checked='checked' />
</center>

<input type='hidden' name='formNum' value='form2' />
<input type='hidden' name='%s' value='%s' />
<input type='hidden' name='updateXML' value='Yes'>

""" % (cdrcgi.SESSION, session)

    # Table contents
    html += \
"""
<hr /><br />
<p>In the following table:</p>
 <ul>
  <li>Doc ID = CDR document ID.</li>
  <li>ProjectedAccrual text = text the program examined, if any found.</li>
  <li>Rule = Name of the rule that was matched, if any.</li>
  <li>Guess = Program's guess based on the rule.</li>
  <li>Override = Place for you to override the guess.</li>
 </ul>
<br />
<table border='1'>
 <tr>
  <th>Doc ID</th>
  <th>ProjectedAccrual text</th>
  <th>Rule</th>
  <th>Guess</th>
  <th>Override</th>
 </tr>
"""
    # Each line
    idx = 0
    for docId in docIds:
        # Retrieve text to scan
        accText = getAccrualText(session, docId)

        # Apply rule set
        (accRule, accNum) = scanAccrualText(accText)

        # Show user
        html += """\
 <tr>
  <td>%d</td>
  <td>%s</td>
  <td>%s</td>
  <td>%d</td>
  <td><input name='docUsrVal%d' type='text' size='5' />
      <input name='docId%d' type='hidden' value='%d' />
      <input name='docVal%d' type='hidden' value='%d' />
  </td>
 </tr>
""" % (docId, accText, accRule, accNum, idx, idx, docId, idx, accNum)
        idx += 1

    # End of form
    html += """\
</FORM>
</BODY>
</HTML>
"""
    return html

def createForm3(session):
    """
    Generate final feedback form.

    Return:
        Form html.
    """

    section = 'Click "More" or Exit to process more documents or exit'
    buttons = ["More", "Exit"]

    html = cdrcgi.header(TITLE, TITLE, section, SCRIPT, buttons) + \
"""
<p>Processing is complete.  Output is either in the GlobalChange
Output directory (if running in test mode), or in the database.<p>

<p>Click "More" to process more protocol documents.</p>
<p>Click "Exit" to return to the Admin Menu.</p>

<input type='hidden' name='formNum' value='form1' />
<input type='hidden' name='%s' value='%s' />

</FORM>
</BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    return html

def getUnprocessedDocIds(numDocs):
    """
    Select document IDs of qualified docs with no ExpectedEnrollment values.
    XXX - REQUIRES INDEX ON /InScopeProtocol/ExpectedEnrollment.

    Orders them by status - putting Active first, then by id.

    Pass:
        Max num doc IDs to fetch.

    Return:
        List of qualifying doc ids.
    """
    try:
        conn   = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
SELECT top %d q1.doc_id
  FROM query_term q1, query_term q3
 WHERE q1.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q1.value = 'ClinicalTrials.gov ID'
   AND NOT EXISTS (
      SELECT q2.doc_id FROM query_term q2
       WHERE q2.doc_id = q1.doc_id
         AND q2.path = '/InScopeProtocol/ExpectedEnrollment')
   AND q3.doc_id = q1.doc_id
   AND q3.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
 ORDER BY q3.value, q1.doc_id
""" % numDocs, timeout=800)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Error fetching document ids: %s" % str(info))

    docIds = []
    for row in rows:
        docIds.append(row[0])
    return (docIds)

def getAccrualText(session, docId):
    """
    Get all of the text of the ProjectedAccrual element.

    Pass:
        docId = CDR document ID.

    Return:
        Text of all subelements of ProjectedAccrual, concatenated
        together and normalized with respect to spaces.

        If no ProjectedAccrual found, returns a constant string.
    """
    global NO_ACCRUAL_TEXT

    # Get and parse the document
    doc = cdr.getDoc(session, docId, getObject=True)
    dom = doc.xml

    # Get ProjectedAccrual element text
    docElem = xml.dom.minidom.parseString(dom).documentElement

    # Default return if no element found
    accrualText = NO_ACCRUAL_TEXT

    # Search DOM for ProjectedAccrual
    for child in docElem.childNodes:
      if child.nodeName == 'ProtocolAbstract':
        for gchild in child.childNodes:
          if gchild.nodeName == 'Professional':
            for ggchild in gchild.childNodes:
              if ggchild.nodeName == 'ProjectedAccrual':
                # Get text of element and all subelements separated by spaces
                accrualText = cdr.getTextContent(ggchild, True, ' ')

                # Normalize results
                accrualText = re.sub(r"\s+", " ", accrualText)
                break
            break
        break

    return accrualText

def armCheck(accText, numPatients):
    """
    Is this "per arm"?  Subroutine of scanAccrualText.
    """

    # Per arm?


def scanAccrualText(accText):
    """
    Scan the text of the ProjectedAccrual element, looking for clues
    to the number of patients.

    This is the heart of the program, or maybe the brain, or maybe the
    Achilles heel.

    Pass:
        accText - Text to scan.

    Return:
        Tuple of:
            Name of rule that was matched (or not matched message).
            A number.  If no number can be generated, then 0.
    """
    global NO_ACCRUAL_TEXT, RULE_SET

    # Default = No enrollment could be guessed.
    accNum  = 0
    accRule = "No check performed"

    # Only bother if there's something to check
    if accText != NO_ACCRUAL_TEXT:

        # Process rules until we find a hit or reach the end
        for ruleGrp in RULE_SET:
            # Handle simple or list rules
            if isinstance(ruleGrp, AccPat):
                ruleList = (ruleGrp,)
            else:
                ruleList = ruleGrp

            # Execute each rule in group, in priority order
            for rule in ruleList:
                (accRule, accNum) = rule.run(accText, accNum)

                # If nothing from the first check, we're done this ruleGrp
                if not accNum:
                    break

            # If we hit this rule group, don't need to go on
            if accNum:
                break

        # If we couldn't find anything, say so
        if not accNum:
            accRule = "No rule matched"


    # Tell caller
    return (accRule, accNum)

#----------------------------------------------------------------------
# Main
#----------------------------------------------------------------------

# Rule table
# Rules are lists of things to try.
# They can be:
#   An object constructor.
#   A list of object constructors to be tried sequentially if the
#     each previous one was successful.
RULE_SET = (\
 AccPat("Total patients", r"total( of)? @@( evaluable)? patients"),
 AccPat("Numbered patients", r"@@ patients"),
 AccPat("Evaluable patients", r"@@( fully)? evaluable patients"),
 AccPat("Eligible patients", r"@@ eligible patients"),
 AccPat("Numbered women", r"@@ women"),
 AccPat("Numbered men", r"@@ men"),
)

# Get any user supplied data
fields    = cgi.FieldStorage()
request   = cdrcgi.getRequest(fields)
session   = cdrcgi.getSession(fields)
formNum   = fields and fields.getvalue('formNum') or None
docCnt    = fields and fields.getvalue('numDocs') or None
testMode  = fields and fields.getvalue('testMode') or None
updateNow = fields and fields.getvalue('updateXML') or None

# User navigation back to main menu or to restart
if request == ADMIN or request == "Exit":
    cdrcgi.navigateTo("Admin.py", session)
if request == "More":
    cdrcgi.navigateTo(SCRIPT, session)

# Global for communication between Filter and Transform
idVals = {}

# Is this the start of a run?
if not request or request == "More":
    # Send start page and restart at the top
    cdrcgi.sendPage(createForm1(session))

# If user supplied some number of docs, process them and generate a form
# Convert document count to integer
numDocs = 0
if formNum == 'form1':
    # Get num docs
    if docCnt:
        numDocs = int(docCnt)
    if numDocs < 1:
        cdrcgi.bail("You must enter a positive integer number of documents")

    # Process
    docIDs = getUnprocessedDocIds(numDocs)
    cdrcgi.sendPage(createForm2(session, docIDs))

# If the user has Submitted a request for updates, do it
if request == 'Submit Request' and formNum == "form2":
    # Need userid and password
    (user, pw) = cdr.idSessionUser(session, session)

    # Start the job
    job = ModifyDocs.Job(user, pw, Filter(), Transform(),
                         "Programmed add of ExpectedEnrollment",
                         testMode=testMode)
    # Don't want stderr log appearing in browser output
    job.suppressStdErrLogging()

    job.run()

    # Report to user
    cdrcgi.sendPage(createForm3(session))
