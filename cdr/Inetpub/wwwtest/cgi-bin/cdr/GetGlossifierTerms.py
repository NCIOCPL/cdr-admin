import cdrdb, re

# XXX CHANGE query_term TO query_term_pub ONCE CONVERSION PROCESSING FINISHED.
# XXX CHANGE document c to pub_proc_cg c BELOW (SEE XXX COMMENT).

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
for docId, dictionary in cursor.fetchall():
    if docId not in dictionaries['en']:
        dictionaries['en'][docId] = set()
    dictionaries['en'][docId].add(dictionary.strip())

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
for docId, language, dictionary in cursor.fetchall():
    language = language and language.strip() or None
    dictionary = dictionary and dictionary.strip() or None
    if language and dictionary:
        if language not in dictionaries:
            dictionaries[language] = {}
        if docId not in dictionaries[language]:
            dictionaries[language][docId] = set()
        dictionaries[language][docId].add(dictionary)
#for language in dictionaries:
#    print language, len(dictionaries[language])

#----------------------------------------------------------------------
# Create a lookup table to find a concept given the name's document ID.
#----------------------------------------------------------------------
conceptIndex = {}
cursor.execute("""\
    SELECT doc_id, int_val
      FROM query_term_pub
     WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'""")
for nameId, conceptId in cursor.fetchall():
    conceptIndex[nameId] = conceptId

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
       AND s.value <> 'Rejected'""")
for docId, name in cursor.fetchall():
    if docId in conceptIndex:
        conceptId = conceptIndex[docId]
        dictionarySet = dictionaries['en'].get(conceptId, None)
        terms['en'][docId] = [Term(docId, name, 'en', dictionarySet)]

#----------------------------------------------------------------------
# Get the variant English names from the external string mapping table.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT m.doc_id, m.value
      FROM external_map m
      JOIN external_map_usage u
        ON u.id = m.usage
     WHERE u.name = 'GlossaryTerm Phrases'""")
for docId, name in cursor.fetchall():
    if docId in terms['en']:
        conceptId = conceptIndex[docId]
        dictionarySet = dictionaries[language].get(conceptId, None)
        term = Term(docId, name, 'en', dictionarySet)
        terms['en'][docId].append(term)

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
     WHERE n.path = '/GlossaryTermName/TranslatedName/TermNameString'
       AND l.path = '/GlossaryTermName/TranslatedName/@language'
       AND s.path = '/GlossaryTermName/TranslatedName/TranslatedNameStatus'
       AND s.value <> 'Rejected'""")
for docId, name, language in cursor.fetchall():
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
#for language in terms:
#    print language, len(terms[language])
###    #print terms[language].keys()
names = {}
WHITESPACE = re.compile(u"\\s+")
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
print """\
Content-type: text/plain

%s""" % repr(names)
