#!/usr/bin/env python3

from cdrcgi import Controller, HTMLPage
from datetime import datetime
from re import compile, sub
from requests import get
from time import sleep


class Control(Controller):

    SUBTITLE = "EVS Drug Concepts Used By More Than One CDR Drug Term"
    LOGNAME = "ambiguous-evs-drug-concepts"
    EVS_MAX_REQUESTS_ALLOWED_PER_SECOND = 3
    EVS_SLEEP = 1 / EVS_MAX_REQUESTS_ALLOWED_PER_SECOND
    EVS_API = "https://api-evsrest.nci.nih.gov/api/v1/concept/ncit"
    FETCH_API = f"{EVS_API}?include=full&list="
    BATCH_SIZE = 100
    BUTTONS = (
        HTMLPage.button(Controller.SUBMENU),
        HTMLPage.button(Controller.ADMINMENU),
        HTMLPage.button(Controller.LOG_OUT),
    )

    def show_form(self):
        return self.show_report()
    def show_report(self):
        opts = dict(
            banner=self.title,
            subtitle=self.subtitle,
            body_classes="report",
            buttons=self.BUTTONS,
            session=self.session,
            action=self.script,
        )
        page = HTMLPage(self.title, **opts)
        for concept in sorted(self.concepts):
            concept.show(page)
        elapsed = datetime.now() - self.started
        count = len(self.concepts)
        footnote = page.B.P(f"{count} concepts; elapsed: {elapsed}")
        footnote.set("class", "footnote")
        page.body.append(footnote)
        page.send()

    @property
    def concepts(self):
        """Concepts associated with more than one CDR document."""

        if not hasattr(self, "_concepts"):
            query = self.Query("query_term", "doc_id", "value")
            query.where("path = '/Term/NCIThesaurusConcept'")
            rows = query.execute(self.cursor).fetchall()
            docs = {}
            for doc_id, code in rows:
                code = code.strip().upper()
                if code not in docs:
                    docs[code] = []
                docs[code].append(doc_id)
            codes = []
            for code in docs:
                if len(docs[code]) > 1:
                    codes.append(code)
            offset = 0
            self._concepts = []
            done = set()
            while offset < len(codes):
                subset = codes[offset:offset+self.BATCH_SIZE]
                offset += self.BATCH_SIZE
                api = self.FETCH_API + ",".join(subset)
                response = get(api)
                for values in response.json():
                    code = values.get("code", "").strip().upper()
                    if code in docs and code not in done:
                        done.add(code)
                        ids = docs[code]
                        self._concepts.append(Concept(self, code, values, ids))
                if offset < len(codes):
                    sleep(self.EVS_SLEEP)
        return self._concepts


class Concept:
    DEFINITION_TYPES = "DEFINITION", "ALT_DEFINITION"
    SUFFIX = compile(r"\s*\(NCI\d\d\)$")
    def __init__(self, control, code, values, doc_ids):
        self.control = control
        self.code = code
        self.values = values
        self.doc_ids = doc_ids
    def show(self, page):
        page.body.append(page.B.H3(f"{self.name} ({self.code})"))
        if self.definition:
            page.body.append(page.B.P(self.definition))
        ul = page.B.UL()
        for doc in sorted(self.docs):
            ul.append(doc.show(page))
        page.body.append(ul)
    def __lt__(self, other):
        return self.sortkey < other.sortkey
    @property
    def definition(self):
        if not hasattr(self, "_definition"):
            definitions = []
            for values in self.values.get("definitions", []):
                if values.get("type") in self.DEFINITION_TYPES:
                    if values.get("source") == "NCI":
                        definition = values.get("definition", "").strip()
                        if definition:
                            definition = self.SUFFIX.sub("", definition)
                            definition = sub(r"^NCI\|", "", definition)
                            definitions.append(definition)
            self._definition = definitions[0] if definitions else ""
        return self._definition
    @property
    def docs(self):
        if not hasattr(self, "_docs"):
            self._docs = []
            for doc_id in self.doc_ids:
                self._docs.append(Doc(self.control, doc_id))
        return self._docs
    @property
    def sortkey(self):
        if not hasattr(self, "_sortkey"):
            self._sortkey = self.name.lower(), self.code
        return self._sortkey
    @property
    def name(self):
        if not hasattr(self, "_name"):
            self._name = self.values.get("name", "").strip()
        return self._name


class Doc:
    def __init__(self, control, doc_id):
        self.control = control
        self.doc_id = doc_id
        query = control.Query("document", "title", "active_status")
        query.where(query.Condition("id", doc_id))
        row = query.execute(control.cursor).fetchone()
        self.title = row.title
        self.blocked = row.active_status != "A"
    def __lt__(self, other):
        return self.title < other.title
    def show(self, page):
        cdr_id = f"CDR{self.doc_id}"
        opts = dict(DocId=cdr_id, Filter="set:QC Term Set")
        url = self.control.make_url("Filter.py", **opts)
        link = page.B.A(cdr_id, href=url, target="_blank")
        pieces = [f"{self.title} (", link, ")"]
        if self.blocked and "BLOCKED" not in self.title:
            pieces.append(" - BLOCKED")
        return page.B.LI(*pieces)


if __name__ == "__main__":
    Control().run()
