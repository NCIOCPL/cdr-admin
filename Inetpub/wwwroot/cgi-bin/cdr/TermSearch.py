#----------------------------------------------------------------------
# Prototype for duplicate-checking interface for Term documents.
#
# BZIssue::4714 (change URL and label for searching Thesaurus)
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import cdrdb
import nci_thesaurus

SEARCH = "https://nciterms.nci.nih.gov"

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
conn        = cdrdb.connect("CdrGuest")
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
boolOp      = fields.getvalue("Boolean")         or "AND"
prefTerm    = fields.getvalue("PrefTerm")        or None
otherName   = fields.getvalue("OtherName")       or None
termType    = fields.getvalue("TermType")        or None
semType     = fields.getvalue("SemType")         or None
submit      = fields.getvalue("SubmitButton")    or None
impReq      = fields.getvalue("ImportButton")    or None
help        = fields.getvalue("HelpButton")      or None
srchThes    = fields.getvalue("SearchThesaurus") or None
conceptCode = fields.getvalue("ConceptCode")     or None
ckPrefNm    = fields.getvalue("CkPrefNm")        or None
updateDefs  = fields.getvalue("UpdateDefs")      or False
updateNames = fields.getvalue("UpdateNames")     or False
updateCDRID = fields.getvalue("UpdateCDRID")     or None
userPair    = cdr.idSessionUser(session, session)
userInfo    = cdr.getUser(session, userPair[0])
subtitle    = "Term"
logger      = cdr.Logging.get_logger("TermSearch")
updates     = None

if help:
    cdrcgi.bail("Sorry, help for this interface has not yet "
                "been developed.")

def to_html(node):
    return cdrcgi.etree.tostring(node, pretty_print=True, method="html")

#----------------------------------------------------------------------
# Callback to generate picklist for term types.
#----------------------------------------------------------------------
def termTypeList(conn, fName):
    B = cdrcgi.Page.B
    try:
        cursor = conn.cursor()
        query = cdrdb.Query("query_term", "value").unique()
        query.where("path = '/Term/TermType/TermTypeName'")
        values = [row[0] for row in query.execute(cursor).fetchall()]
    except Exception, e:
        cdrcgi.bail('Failure retrieving term type list from CDR: %s' % e)
    select = B.SELECT(name="%s")
    select.append(B.OPTION(u"\xa0", value="", checked="checked"))
    for value in values:
        select.append(B.OPTION(value + u" \xa0", value=value))
    return to_html(select)

#----------------------------------------------------------------------
# Callback to generate picklist for semantic types.
#----------------------------------------------------------------------
def semanticTypeList(conn, fName):
    B = cdrcgi.Page.B
    try:
        cursor = conn.cursor()
        query = cdrdb.Query("document d", "d.id", "d.title").unique()
        query.join("query_term t", "t.int_val = d.id")
        query.where("t.path = '/Term/SemanticType/@cdr:ref'")
        rows = query.order("d.title").execute(cursor).fetchall()
        cursor.close()
    except Exception, e:
        cdrcgi.bail('Failure retrieving semantic type list from CDR: %s' % e)
    select = B.SELECT(name="%s")
    select.append(B.OPTION(u"\xa0", value="", checked="checked"))
    for id, title in rows:
        id = cdr.normalize(id)
        select.append(B.OPTION(title + u" \xa0", value=id))
    return to_html(select)

#----------------------------------------------------------------------
# Show the changes made to the updated Term document.
#----------------------------------------------------------------------
def make_change_list(changes):
    logger.info("changes: %s", changes)
    B = cdrcgi.Page.B
    ul = B.UL()
    for change in changes:
        if "definition" not in change.lower():
            ul.append(B.LI(change))
    for change in changes:
        if "definition" in change.lower():
            ul.append(B.LI(change))
    td = B.TD(ul, style="border: solid black 2px; padding: 15px 15px 0 0")
    return to_html(B.TABLE(B.TR(td), style="margin-bottom: 25px"))

#----------------------------------------------------------------------
# Import a citation document from NCI Thesaurus.
#----------------------------------------------------------------------
if impReq:
    if not conceptCode:
        cdrcgi.bail("No concept code provided")
    if not session:
        cdrcgi.bail("User not logged in")
    try:
        concept = nci_thesaurus.Concept(code=conceptCode)
    except Exception, e:
        logger.exception("unable to load %r", conceptCode)
        cdrcgi.bail("importing concept from NCI Thesaurus: %s" % e)
    opts = {
        "skip_other_names": False, # XXX not updateNames,
        "skip_definitions": False # XXX not updateDefs
    }
    try:
        if updateCDRID:
            changes = concept.update(session, updateCDRID, **opts)
            if changes:
                subtitle = "New version created"
                updates = make_change_list(changes)
            else:
                subtitle = "No changes found to save"
        else:
            subtitle = concept.add(session)#, **opts)
    except Exception, e:
        logger.exception("unabled to add/update %r", conceptCode)
        cdrcgi.bail(str(e))
    finally:
        if updateCDRID:
            cdr.unlock(session, updateCDRID)

#----------------------------------------------------------------------
# Create additional fields for importing/updating Term documents.
#----------------------------------------------------------------------
def make_import_fields():
    B = cdrcgi.Page.B
    table = B.TABLE()
    import_fields = (
        ("ConceptCode", "Concept Code of Term to Import:"),
        ("UpdateCDRID", "CDR ID of Document to Update:")
    )
    for name, label in import_fields:
        label = B.SPAN(label, B.CLASS("import-label page"))
        field = B.INPUT(name=name, id=name)
        table.append(B.TR(B.TD(label, align="right"), B.TD(field)))
    note = "(Concept Code also required to Update)"
    table.append(B.TR(B.TD(B.SPAN(note, B.CLASS("import-note page")))))
    options = (
        ("UpdateDefs", "Update Definitions"),
        ("UpdateNames", "Update Names")
    )
    opts = { "type": "checkbox", "value": "true", "checked": "checked" }
    for name, label in options:
        checkbox = B.INPUT(id=name, name=name, **opts)
        checkbox.tail = label
        # XXX table.append(B.TR(B.TD(), B.TD(checkbox)))
    button = B.INPUT(type="submit", name="ImportButton", value="Import")
    table.append(B.TR(B.TD(), B.TD(button)))
    rules = (
        "* { font-family: Arial, sans-serif; }",
        ".import-label { text-align: right; padding-right: 10px; }",
        ".import-note.page  { font-size: 10pt; }",
        "input[type=checkbox] { margin-right: 10px; }"
    )
    style = B.STYLE("\n".join(rules))
    return to_html(B.CENTER(style, table))

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    search_button = "javascript:window.open('%s', 'st')" % SEARCH
    fields = (('Preferred Name',          'PrefTerm'),
              ('Other Name',              'OtherName'),
              ('Term Type',               'TermType', termTypeList),
              ('Semantic Type',           'SemType', semanticTypeList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'),
               ('button', search_button,  'Search NCI Thesaurus'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Term Search Form",
                                          "TermSearch.py",
                                          fields,
                                          buttons,
                                          subtitle,
                                          conn,
                                          updates)

    footer = u"""\
  </FORM>
 </BODY>
</HTML>
"""

    # Suppress the display for Concept Code Import for Guest accounts
    # ---------------------------------------------------------------
    if 'GUEST' in userInfo.groups and len(userInfo.groups) < 2:
        html = page + footer
    else:
        html = page + make_import_fields() + footer

    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (
    cdrcgi.SearchField(prefTerm,  ("/Term/PreferredName",)),
    cdrcgi.SearchField(otherName, ("/Term/OtherName/OtherTermName",)),
    cdrcgi.SearchField(termType,  ("/Term/TermType/TermTypeName",)),
    cdrcgi.SearchField(semType,   ("/Term/SemanticType/@cdr:ref",)),
)

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields,
                                                       boolOp,
                                                       "Term")
if not query:
    cdrcgi.bail('No query criteria specified')

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Term documents: %s' %
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Term", rows, strings,
                                        'set:QC Term Set')

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
