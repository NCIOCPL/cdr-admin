#----------------------------------------------------------------------
#
# $Id: GetGlossifierTerms.py,v 1.4 2009-07-05 19:50:23 bkline Exp $
#
# Program to extract glossary terms for glossifier service invoked by
# Cancer.gov.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2008/11/25 21:08:25  bkline
# Added check for new ExcludeFromGlossifier attribute; fixed query errors.
#
# Revision 1.2  2008/11/24 14:53:30  bkline
# Rewritten to use new GlossaryTermName documents.
#
#----------------------------------------------------------------------
import cdrdb, re, cdr, socket, sys

DEBUG = len(sys.argv) > 1 and sys.argv[1] == '--debug' or False

#----------------------------------------------------------------------
# Send a report on duplicate name+language+dictionary mappings.
#----------------------------------------------------------------------
def reportDuplicate(name, docIds, language, dictionary):
    recips = cdr.getEmailList('GlossaryDupGroup') or ['***REMOVED***']
    server = socket.gethostname().split('.')[0].upper()
    sender = "CDR@%s.NCI.NIH.GOV" % server
    subject = "DUPLICATE GLOSSARY TERM NAME MAPPINGS ON %s" % server
    body = [u"The string '%s' " % name.upper(),
            u"is mapped on %s to the following CDR GlossaryTermName" % server,
            u"documents for language '%s' " % language,
            u"and dictionary '%s'; " % dictionary,
            u"mappings for any phrase+language+dictionary ",
            u"combination (ignoring case) must be unique.  Please correct ",
            u"the data so that this requirement is met.  You may need to ",
            u"look at the External Map Table for Glossary Terms to find ",
            u"some of the mappings.\n\n"]
    for docId in docIds:
        body.append(u"CDR%010d\n" % docId)
    cdr.sendMail(sender, recips, subject, u"".join(body), False, True)

def reportDuplicates(allDups):
    recips = cdr.getEmailList('GlossaryDupGroup') or ['***REMOVED***']
    server = socket.gethostname().split('.')[0]
    sender = "cdr@%s.nci.nih.gov" % server.lower()
    subject = "DUPLICATE GLOSSARY TERM NAME MAPPINGS ON %s" % server.upper()
    body = [u"The following %d sets of duplicate glossary " % len(allDups),
            u"mappings were found in the CDR on %s.  " % server.upper(),
            u"Mappings for any phrase + language + dictionary must be ",
            u"unique.  Please correct the data so that this requirements is ",
            u"met.  You may need to look at the External Map Table for ",
            u"Glossary Terms to find some of the mappings.\n"]
    keys = allDups.keys()
    keys.sort()
    for key in keys:
        name, language, dictionary = key
        body.append(u"\n%s (language='%s' dictionary='%s')\n" %
                    (name.upper(), language, dictionary))
        for docId in allDups[key]:
            body.append(u"\tCDR%010d\n" % docId)
    cdr.sendMail(sender, recips, subject, u"".join(body), False, True)

#----------------------------------------------------------------------
# See if we've already seen this name+language+dictionary combo.
# If so, we record it in a map ('duplicates') whose key is a tuple
# of language and dictionary and whose value is a sequence of
# CDR document IDs to which the name is mapped for this language
# and dictionary.
#----------------------------------------------------------------------
def checkForDuplicate(docId, key, keys, duplicates):
    if key in keys:
        if key in duplicates:
            duplicates[key].append(docId)
        else:
            duplicates[key] = [keys[key], docId]
    else:
        keys[key] = docId
    
#----------------------------------------------------------------------
# Make sure we don't have any duplicate name+language+dictionary
# combinations.  If we find any, we report them, and we replace
# the mappings to eliminate them from what we use to provide Cancer.gov
# with glossification services.
#----------------------------------------------------------------------
def checkForDuplicates(name, names, allDups):
    duplicates = {}
    keys = {}
    mappings = names[name]
    for docId in mappings:
        gtnDoc = mappings[docId]
        for language in gtnDoc:
            for dictionary in gtnDoc[language]:
                checkForDuplicate(docId, (language, dictionary), keys,
                                  duplicates)
            if not dictionaries:
                checkForDuplicate(docId, (language, None), keys, duplicates)
    if duplicates:
        for key in duplicates:
            if name.lower() not in ('tpa', 'cab', 'ctx'):
                language, dictionary = key
                allDups[(name, language, dictionary)] = duplicates[key]
                # reportDuplicate(name, duplicates[key], language, dictionary)
        newMap = {}
        for docId in mappings:
            gtnDoc = mappings[docId]
            for language in gtnDoc:
                for dictionary in gtnDoc[language]:
                    if (language, dictionary) not in duplicates:
                        if docId not in newMap:
                            newMap[docId] = {}
                        if language not in newMap[docId]:
                            newMap[docId][language] = set()
                        newMap[docId][language].add(dictionary)
                if not gtnDoc[language]:
                    if (language, None) not in duplicates:
                        if docId not in newMap:
                            newMap[docId] = {}
                        if language not in newMap[docId]:
                            newMap[docId][language] = set()
        if newMap:
            names[name] = newMap
        else:
            del names[name]
        
#----------------------------------------------------------------------
# Convert whitespace sequences to single space, and typesetting single
# quote to apostrophe (CG team didn't want to map typesetting double
# quote marks).
#----------------------------------------------------------------------
def normalize(me):
    if not me:
        return u""
    return re.sub(u"\\s+", " ", me
                  .replace('\u2019', u"'")
                  #.replace('\u201C', u'"')
                  #.replace('\u201D', u'"')
                  .lower().strip())

#----------------------------------------------------------------------
# Get the dictionaries for the English glossary terms.
#----------------------------------------------------------------------
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT doc_id, value
      FROM query_term_pub
     WHERE path = '/GlossaryTermConcept/TermDefinition/Dictionary'""")
dictionaries = { 'en': {} }
rows = cursor.fetchall()
for docId, dictionary in rows:
    if docId not in dictionaries['en']:
        dictionaries['en'][docId] = set()
    dictionaries['en'][docId].add(dictionary.strip())
if DEBUG:
    sys.stderr.write("%d spanish definitions examined\n" % len(rows))

#----------------------------------------------------------------------
# Get the dictionaries for the translated definitions.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT l.doc_id, l.value, d.value
      FROM query_term_pub l
      JOIN query_term_pub d
        ON l.doc_id = d.doc_id
       AND LEFT(l.node_loc, 4) = LEFT(d.node_loc, 4)
     WHERE l.path = '/GlossaryTermConcept/TranslatedTermDefinition/@language'
       AND d.path = '/GlossaryTermConcept/TranslatedTermDefinition/Dictionary'
""")
rows = cursor.fetchall()
for docId, language, dictionary in rows:
    language = language and language.strip() or None
    dictionary = dictionary and dictionary.strip() or None
    if language and dictionary:
        if language not in dictionaries:
            dictionaries[language] = {}
        if docId not in dictionaries[language]:
            dictionaries[language][docId] = set()
        dictionaries[language][docId].add(dictionary)
if DEBUG:
    sys.stderr.write("%d spanish definitions examined\n" % len(rows))

#----------------------------------------------------------------------
# Create a lookup table to find a concept given the name's document ID.
#----------------------------------------------------------------------
conceptIndex = {}
cursor.execute("""\
    SELECT doc_id, int_val
      FROM query_term_pub
     WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'""")
rows = cursor.fetchall()
for nameId, conceptId in rows:
    conceptIndex[nameId] = conceptId
if DEBUG:
    sys.stderr.write("%d links to concept documents\n" % len(rows))

#----------------------------------------------------------------------
# An object of this class holds information about a glossary term name
# string.
#----------------------------------------------------------------------
class Term:
    def __init__(self, docId, name, language, dictionaries):
        self.docId        = docId
        self.name         = name
        self.language     = language
        self.dictionaries = dictionaries

#----------------------------------------------------------------------
# Collect the English names.
#----------------------------------------------------------------------
terms = { 'en': {} }
cursor.execute("""\
    SELECT n.doc_id, n.value
      FROM query_term_pub n
      JOIN pub_proc_cg c
        ON c.id = n.doc_id
      JOIN query_term_pub s
        ON s.doc_id = n.doc_id
     WHERE n.path = '/GlossaryTermName/TermName/TermNameString'
       AND s.path = '/GlossaryTermName/TermNameStatus'
       AND s.value <> 'Rejected'""")
rows = cursor.fetchall()
for docId, name in rows:
    if docId in conceptIndex:
        conceptId = conceptIndex[docId]
        dictionarySet = dictionaries['en'].get(conceptId, None)
        terms['en'][docId] = [Term(docId, name, 'en', dictionarySet)]
if DEBUG:
    sys.stderr.write("%d english term names\n" % len(rows))

#----------------------------------------------------------------------
# Get the variant English names from the external string mapping table.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT m.doc_id, m.value
      FROM external_map m
      JOIN external_map_usage u
        ON u.id = m.usage
     WHERE u.name = 'GlossaryTerm Phrases'""")
rows = cursor.fetchall()
for docId, name in rows:
    if docId in terms['en']:
        conceptId = conceptIndex[docId]
        dictionarySet = dictionaries[language].get(conceptId, None)
        term = Term(docId, name, 'en', dictionarySet)
        terms['en'][docId].append(term)
if DEBUG:
    sys.stderr.write("%d english variant names\n" % len(rows))

#----------------------------------------------------------------------
# Collect the translated names.
#----------------------------------------------------------------------
cursor.execute("""\
         SELECT n.doc_id, n.value, l.value
           FROM query_term_pub n
           JOIN query_term_pub l
             ON n.doc_id = l.doc_id
            AND LEFT(n.node_loc, 4) = LEFT(l.node_loc, 4)
           JOIN query_term_pub s
             ON s.doc_id = n.doc_id
            AND LEFT(n.node_loc, 4) = LEFT(s.node_loc, 4)
LEFT OUTER JOIN query_term_pub e
             ON e.doc_id = n.doc_id
            AND LEFT(n.node_loc, 4) = LEFT(e.node_loc, 4)
            AND e.path = '/GlossaryTermName/TranslatedName'
                       + '/@ExcludeFromGlossifier'
          WHERE n.path = '/GlossaryTermName/TranslatedName/TermNameString'
            AND l.path = '/GlossaryTermName/TranslatedName/@language'
            AND s.path = '/GlossaryTermName/TranslatedName/TranslatedNameStatus'
            AND s.value <> 'Rejected'
            AND (e.value IS NULL OR e.value <> 'Yes')""")
rows = cursor.fetchall()
if DEBUG:
    sys.stderr.write("%d Spanish names names\n" % len(rows))
for docId, name, language in rows:
    if docId in terms['en']:
        if language not in terms:
            terms[language] = {}
        if language not in dictionaries:
            dictionaries[language] = {}
        conceptId = conceptIndex[docId]
        dictionarySet = dictionaries[language].get(conceptId, None)
        term = Term(docId, name, language, dictionarySet)
        if docId not in terms[language]:
            terms[language][docId] = [term]
        else:
            terms[language][docId].append(term)
names = {}
for language in terms:
    langTerms = terms[language]
    for docId in langTerms:
        for term in langTerms[docId]:
            name = normalize(term.name)
            if name not in names:
                names[name] = {}
            if docId not in names[name]:
                names[name][docId] = {}
            if language not in names[name][docId]:
                names[name][docId][language] = set()
            if term.dictionaries:
                names[name][docId][language].update(term.dictionaries)
keys = names.keys()
allDups = {}
for key in keys:
    checkForDuplicates(key, names, allDups)
if allDups:
    reportDuplicates(allDups)
print """\
Content-type: text/plain

%s""" % repr(names)
