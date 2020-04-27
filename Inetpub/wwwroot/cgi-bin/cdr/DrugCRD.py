#!/usr/bin/env python

"""Report to list the Comprehensive Review Dates for drug information docs.
"""

from datetime import date
from cdrcgi import Controller, Reporter


class Control(Controller):
    """One master class to rule them all."""

    SUBTITLE = "Drugs Comprehensive Review Dates"
    TYPES = "single_agent", "combination"
    RADIO_BUTTONS = (
        (
            "show_all", "Display Review Dates",
            (
                ("N", "Show only last review date"),
                ("Y", "Show all review dates"),
            ),
        ),
        (
            "show_id", "ID Display",
            (
                ("N", "Without CDR ID"),
                ("Y", "With CDR ID"),
            ),
        ),
        (
            "show_unpub", "Version Display",
            (
                ("N", "Publishable only"),
                ("Y", "Publishable and non-publishable"),
            ),
        ),
    )


    def build_tables(self):
        """Assemble the tables to be rendered for the report."""

        if not self.agent_types:
            self.bail("At least one agent type must be selected")
        return [agent_type.table for agent_type in self.agent_types]

    def populate_form(self, page):
        """Add the fields to the form page.

        Pass:
            page - object on which the form lives
        """

        fieldset = page.fieldset("Select Agent Type(s)")
        for value in self.TYPES:
            label = value.replace("_", " ").title() + " Drug"
            opts = dict(label=label, value=value, checked=True)
            fieldset.append(page.checkbox("type", **opts))
        page.form.append(fieldset)
        for name, label, values in self.RADIO_BUTTONS:
            fieldset = page.fieldset(label)
            checked = True
            for value, label in values:
                opts = dict(checked=checked, value=value, label=label)
                fieldset.append(page.radio_button(name, **opts))
                checked = False
            page.form.append(fieldset)
        page.add_output_options("html")

    @property
    def agent_types(self):
        """Drug agent types selected by the user for the report."""

        if not hasattr(self, "_agent_types"):
            types = self.fields.getlist("type")
            self._agent_types = [AgentType(self, t) for t in types]
        return self._agent_types

    @property
    def columns(self):
        """Column headers for the report."""

        if not hasattr(self, "_columns"):
            columns = []
            if self.show_id:
                columns.append(self.Reporter.Column("CDR ID", width="50px"))
            columns.extend([
                self.Reporter.Column("Doc Title", width="400px"),
                self.Reporter.Column("Date", width="75px"),
            ])
            self._columns = columns
        return self._columns

    @property
    def show_all(self):
        """Show all dates (instead of just the last one)?"""

        if not hasattr(self, "_show_all"):
            self._show_all = self.fields.getvalue("show_all") == "Y"
        return self._show_all

    @property
    def show_id(self):
        """True if the report should include a column for the CDR IDs."""

        if not hasattr(self, "_show_id"):
            self._show_id = self.fields.getvalue("show_id") == "Y"
        return self._show_id

    @property
    def show_unpub(self):
        """True if the report should include unpublished summaries."""

        if not hasattr(self, "_show_unpub"):
            self._show_unpub = self.fields.getvalue("show_unpub") == "Y"
        return self._show_unpub

    @property
    def subtitle(self):
        """What we show under the main banner."""

        if self.request != self.SUBMIT:
            return self.SUBTITLE
        return f"{self.SUBTITLE} ({date.today()})"

    @property
    def title(self):
        """What we show for the main banner."""

        if self.request != self.SUBMIT:
            return self.TITLE
        return "PDQ Drug Summary Comprehensive Review Report"


class AgentType:
    """Subset of drug summaries based on drug agent type."""

    DOCTYPE = "DrugInformationSummary"
    COMBO_PATH = f"/{DOCTYPE}/DrugInfoMetaData/DrugInfoType/@Combination"

    def __init__(self, control, type_name):
        """Remember the caller's values.

        Pass:
            control - access to the fields and the database
            type_name - "single_agent" or "combination"
        """

        self.__control = control
        self.__type_name = type_name

    @property
    def caption(self):
        """What to display at the top of the table."""
        if self.__type_name == "combination":
            return "Combination Drugs"
        return "Single Agent Drugs"

    @property
    def docs(self):
        """Drug information summaries of this agent type."""

        if not hasattr(self, "_docs"):
            suffix = "" if self.__control.show_unpub else "_pub"
            query_term = f"query_term{suffix}"
            fields = "t.doc_id", "t.value"
            query = self.__control.Query(f"{query_term} t", *fields)
            query.where(f"t.path = '/{self.DOCTYPE}/Title'")
            if self.__type_name == "combination":
                query.join(f"{query_term} c", "c.doc_id = t.doc_id")
                query.where(f"c.path = '{self.COMBO_PATH}'")
                query.where("c.value = 'Yes'")
            else:
                query.outer(f"{query_term} c", "c.doc_id = t.doc_id",
                            f"c.path = '{self.COMBO_PATH}'", "c.value = 'Yes'")
                query.where("c.doc_id IS NULL")
            self.__control.logger.info("query:\n%s", query)
            rows = query.unique().execute(self.__control.cursor).fetchall()
            self._docs = [Drug(self.__control, *row) for row in rows]
        return self._docs

    @property
    def table(self):
        """Report table for drugs of this action type."""

        if not hasattr(self, "_table"):
            opts = dict(
                caption=self.caption,
                sheet_name=self.__type_name,
                columns=self.__control.columns,
            )
            rows = []
            for doc in sorted(self.docs):
                rows += doc.rows
            self._table = Reporter.Table(rows, **opts)
        return self._table

    def __lt__(self, other):
        "Support sorting by caption."
        return self.caption < other.caption


class Drug:
    """Drug information summary document."""

    REVIEW_DATE_PATH = f"/{AgentType.DOCTYPE}/ComprehensiveReviewDate"
    DATE_TYPE_PATH = f"{REVIEW_DATE_PATH}/@DateType"

    def __init__(self, control, doc_id, title):
        self.__control = control
        self.__doc_id = doc_id
        self.__title = title

    @property
    def control(self):
        """Access to the report settings and the database."""
        return self.__control

    @property
    def doc_id(self):
        """CDR ID of this DrugInformationSummary document."""
        return self.__doc_id

    @property
    def rows(self):
        """Report table row(s) for this drug document."""

        if not hasattr(self, "_rows"):
            reviews = self.reviews or [""]
            if not self.control.show_all:
                reviews = reviews[-1:]
            self._rows = []
            for review in reviews:
                row = [self.title, review]
                if self.control.show_id:
                    row.insert(0, self.doc_id)
                self._rows.append(row)
        return self._rows

    @property
    def reviews(self):
        """Sequence of comprehensive review dates for this drug document."""

        if not hasattr(self, "_reviews"):
            query = self.control.Query("query_term", "value")
            query.where(query.Condition("doc_id", self.doc_id))
            query.where(query.Condition("path", self.REVIEW_DATE_PATH))
            rows = query.execute(self.control.cursor).fetchall()
            self._reviews = sorted([row.value for row in rows])
        return self._reviews

    @property
    def title(self):
        """Title for this drug document."""
        return self.__title

    def __lt__(self, other):
        return self.title.upper() < other.title.upper()


class Review:
    "Information about a single proposed or actual comprehensive review"
    def __init__(self, date, state):
        self.date = date
        self.state = state

    def __lt__(self, other):
        "Support sorting reviews in chronological order"
        return (self.date, self.state) < (other.date, other.state)


if __name__ == "__main__":
    "Allow import (by doc or lint tools, for example) without side effects"
    Control().run()
