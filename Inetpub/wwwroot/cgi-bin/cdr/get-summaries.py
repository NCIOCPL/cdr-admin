#!/usr/bin/env python
"""JSON API for fetching the information about PDQ summaries.

The limit parameter can be used to restrict the set of boards returned
to the first N summaries for each summary type. For example:

    GET /cgi-bin/cdr/get-summaries.py?limit=5

The include-unpublished parameter can be used to get summaries which
are not published. For example:

    GET /cgi-bin/cdr/get-summaries.py?include-unpublished=true

The modules-only  parameter can be used to get Summary documents which
can only be used as modules, instead of summaries which can be published
on their own (the default). For example:

    GET /cgi-bin/cdr/get-summaries.py?modules-only=true
"""

from collections import defaultdict
from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-summaries API service"
    LOGNAME = "testing"
    BN_PATH = "/Organization/OrganizationNameInformation/OfficialName/Name"
    BT_PATH = "/Organization/OrganizationType"
    BOARD_TYPES = "PDQ Advisory Board", "PDQ Editorial Board"

    def run(self):
        """Overridden because this is not a standard report."""

        opts = dict(mime_type="application/json")
        self.send_page(dumps(self.summaries, indent=2), **opts)

    @cached_property
    def boards(self):
        """Dictionary of board names indexed by board ID."""

        query = self.Query("query_term n", "n.doc_id", "n.value")
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.join("active_doc a", "a.id = n.doc_id")
        query.where(query.Condition("n.path", self.BN_PATH))
        query.where(query.Condition("t.path", self.BT_PATH))
        query.where(query.Condition("t.value", self.BOARD_TYPES, "IN"))
        query.unique()
        boards = {}
        for id, name in query.execute(self.cursor).fetchall():
            boards[id] = name
        return boards

    @cached_property
    def include_unpublished(self):
        """True if we should include summaries which are not published."""
        return True if self.fields.getvalue("include-unpublished") else False

    @cached_property
    def limit(self):
        """Optional throttle on the number of summaries to return per type."""
        return int(self.fields.getvalue("limit", "0"))

    @cached_property
    def modules_only(self):
        """True if we want modules instead of stand-alone summaries."""
        return True if self.fields.getvalue("modules-only") else False

    @cached_property
    def summaries(self):
        """PDQ Summaries, grouped by summary type."""

        query = self.Query("query_term t", "t.doc_id", "t.value").order(1)
        query.where("t.path = '/Summary/SummaryTitle'")
        if not self.include_unpublished:
            query.join("active_doc a", "a.id = t.doc_id")
            if not self.modules_only:
                query.join("pub_proc_cg c", "c.id = t.doc_id")
        if self.modules_only:
            query.join("query_term m", "m.doc_id = t.doc_id")
            query.where("m.path = '/Summary/@ModuleOnly'")
        elif self.include_unpublished:
            conditions = (
                "m.doc_id = t.doc_id",
                "m.value = 'Yes'",
                "m.path = '/Summary/@ModuleOnly'",
            )
            query.outer("query_term m", *conditions)
            query.where("m.doc_id IS NULL")
        query.log()
        summaries = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for id, title in query.execute(self.cursor).fetchall():
            summary_language = self.summary_languages.get(id)
            summary_type = self.summary_types.get(id)
            summary_audience = self.summary_audiences.get(id)
            node = summaries[summary_language][summary_type][summary_audience]
            if not self.limit or len(node) < self.limit:
                boards = []
                for board_id in sorted(self.summary_boards.get(id, [])):
                    board = dict(id=board_id, name=self.boards.get(board_id))
                    boards.append(board)
                node.append(dict(id=id, title=title, boards=boards))
        return summaries

    @cached_property
    def summary_audiences(self):
        """Dictionary mapping summary IDs to audiences."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Summary/SummaryMetaData/SummaryAudience'")
        summaries = {}
        for id, audience in query.execute(self.cursor).fetchall():
            summaries[id] = audience
        return summaries

    @cached_property
    def summary_boards(self):
        """Map of boards responsible for each summary."""

        path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        query = self.Query("query_term", "doc_id", "int_val")
        query.where(f"path = '{path}'")
        summaries = defaultdict(set)
        for summary_id, board_id in query.execute(self.cursor).fetchall():
            summaries[summary_id].add(board_id)
        return summaries

    @cached_property
    def summary_languages(self):
        """Dictionary mapping summary IDs to languages."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Summary/SummaryMetaData/SummaryLanguage'")
        summaries = {}
        for id, language in query.execute(self.cursor).fetchall():
            summaries[id] = language
        return summaries

    @cached_property
    def summary_types(self):
        """Dictionary mapping summary IDs to types."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Summary/SummaryMetaData/SummaryType'")
        summaries = {}
        for id, type in query.execute(self.cursor).fetchall():
            summaries[id] = type
        return summaries


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure getting summaries")
        message = f"Failure fetching summaries: {e}"
        control.send_page(message, text_type="plain")
