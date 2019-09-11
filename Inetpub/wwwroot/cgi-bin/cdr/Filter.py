#----------------------------------------------------------------------
# Transform a CDR document using an XSL/T filter and send it back to
# the browser.
#
# BZIssue::846 - Support insertion/deletion revision levels
# BZIssue::846 - Allow display of glossary terms and standard wording
# BZIssue::1683 - Allow display of editorial and advisory board markup
# BZIssue::1883 - Support for choosing audience in GlossaryTerm RS reports
# BZIssue::3923 - Replace pyXML with lxml for validation
# BZIssue::2920 - Allow display of internal/external comments
# BZIssue::3923 - Minor modifications to make HTML output valid
# BZIssue::4123 - Added support for specifying a DTD file
# BZIssue::4560 - Converted output to unicode to match sendPage requirements
# BZIssue::4781 - Have certain links to unpublished docs ignored
# BZIssue::4800 - Glossary Term Link error
# Rewritten July 2015 as part of security sweep.
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import cdrpub
import os
import pickle
import urllib
from cdrapi.settings import Tier

class Control(cdrcgi.Control):
    """
    Encapsulates the logic for this script. The user has three choices:
     1. Run the document through one or more filters and show the result.
     2. Filter the document, validate it, and show the warnings and errors.
     3. Show all of the filter sets which contain the specified filters.
    """

    FILTER = "Submit Filter Request"
    VALIDATE = "Filter and Validate"
    QCSETS = "QC Filter Sets"
    TITLE = "CDR Filtering"
    CACHE = cdr.BASEDIR + "/reports/expanded-filter-sets"
    USE_CACHE = "use"
    REFRESH_CACHE = "refresh"
    TIER = Tier()

    def __init__(self):
        """
        Collect the CGI parameters and make sure they haven't been
        tampered with.
        """
        cdrcgi.Control.__init__(self)
        fields = self.fields
        self.session = "guest"
        self.cache = self.fields.getvalue("cache", self.USE_CACHE)
        if self.cache not in (self.USE_CACHE, self.REFRESH_CACHE):
            cdrcgi.bail()
        self.dtd = fields.getvalue("newdtd", cdr.DEFAULT_DTD)
        doc_id = fields.getvalue(cdrcgi.DOCID)
        if not doc_id:
            cdrcgi.bail("No Document", self.TITLE)
        try:
            self.cdr_id, self.doc_id, fragment = cdr.exNormalize(doc_id)
        except:
            cdrcgi.bail("Unrecognized document ID format")
        version = fields.getvalue("DocVer", "0")
        if version.isdigit():
            self.version = int(version)
        else:
            versions = cdr.lastVersions("guest", self.cdr_id)
            if not versions:
                cdrcgi.bail("Document is not versioned")
            if version == "last":
                self.version = versions[0]
            elif version == "lastp":
                self.version = versions[1]
            else:
                cdrcgi.bail("Version can only be 'last', 'lastp', or an "
                            "integer")
        self.filters = fields.getlist("filter")

        # Backward compatibility
        for i in range(16):
            name = cdrcgi.FILTER
            if i:
                name += str(i)
            value = fields.getvalue(name)
            if value:
                self.filters.append(value)

        # Make sure the filters are legitimate.
        filters = cdr.getFilters("guest")
        sets = cdr.getFilterSets("guest")
        self.filter_sets = dict([(s.name.upper(), s.id) for s in sets])
        self.all_filters = dict([(f.name.upper(), f.id) for f in filters])
        self.all_filter_ids = set([f.id for f in filters])
        for filter_spec in self.filters:
            self.check_filter(filter_spec)
        self.validate = fields.getvalue("validate") == "Y"
        self.qc_sets = fields.getvalue("qcFilterSets") == "Y"
        if not self.filters and not self.qc_sets:
            cdrcgi.bail("No filter", self.TITLE)
        self.ins_levels = []
        for level in ("publish", "approved", "proposed", "rejected"):
            if fields.getvalue(level) == "true":
                self.ins_levels.append(level)# += "%s_" % level
        self.ins_levels += fields.getvalue("insRevLevels", "")
        self.del_levels = fields.getvalue("rsmarkup") == "false"
        self.boards = []
        for board in ("editorial", "advisory"):
            if fields.getvalue(board) == "true":
                self.boards.append("%s-board" % board)
        self.audiences = []
        for audience in ("patient", "hp"):
            if fields.getvalue("gloss" + audience) == "true":
                self.audiences.append(audience)
        if fields.getvalue("QC") == "true":
            self.vendor_or_qc = "QC"
        else:
            self.vendor_or_qc = fields.getvalue("vendorOrQC", "")
        self.comments = "N"
        if fields.getvalue("internal") == "true":
            self.comments = "I"
        if fields.getvalue("external") == "true":
            self.comments = self.comments == "I" and "A" or "E"
        self.glossary = fields.getvalue("glossary") == "true"
        self.standard_wording = fields.getvalue("stdword") == "true"
        self.is_pp = fields.getvalue("ispp") == "true"
        self.is_qc = fields.getvalue("isqc") == "true"
        self.loeref = fields.getvalue("loeref") == "true"

    def run(self):
        "Figure out what the user asked us to do and do it."
        if self.qc_sets:
            self.qc_filter_sets()
        elif self.validate:
            self.filter_and_validate()
        else:
            self.show_filtered_doc()

    def qc_filter_sets(self):
        """
        Show the user the filter sets that contain the selected
        filter(s). Skip over named sets specified by the user.
        """
        filter_ids = []
        for f in self.filters:
            if not f.startswith("set:"):
                if f.startswith("name:"):
                    name = f[5:]
                    filter_id = self.all_filters.get(name.upper())
                    if not filter_id:
                        cdrcgi.bail("Unknown filter: %s" % name)
                elif not f.startswith("set:"):
                    filter_id = f
                try:
                    filter_ids.append(cdr.exNormalize(filter_id)[1])
                except:
                    cdrcgi.bail("Invalid filter %s" % repr(filter_id))
        id_set = set(filter_ids)
        columns = (
            cdrcgi.Report.Column("Set Name"),
            cdrcgi.Report.Column("Action"),
            cdrcgi.Report.Column("Set Detail")
        )
        cache_warning = None
        if self.cache == self.USE_CACHE:
            fp = open(self.CACHE)
            filter_sets = pickle.load(fp)
            fp.close()
        else:
            filter_sets = cdr.expandFilterSets("guest")
            try:
                fp = open(self.CACHE, "w")
                pickle.dump(filter_sets, fp)
                fp.close()
            except Exception as e:
                cache_warning = "Failure refreshing filter set cache: %s" % e
        opts = {
            cdrcgi.DOCID: self.cdr_id,
            "DocVer": str(self.version)
        }
        if self.vendor_or_qc:
            opts["vendorOrQC"] = self.vendor_or_qc
        rows = []
        for set_name in sorted(filter_sets):
            filter_set = filter_sets[set_name]
            if self.set_wanted(filter_set, id_set):
                opts["filter"] = [m.id for m in filter_set.members]
                args = urllib.urlencode(opts, True)
                rows.append((
                    set_name,
                    ActionCell(self.script, args),
                    [u"%s:%s" % (m.id, m.name) for m in filter_set.members]
                ))
        opts = {
            "html_callback_pre": self.show_cache_warning,
            "user_data": cache_warning
        }
        table = cdrcgi.Report.Table(columns, rows, **opts)
        title = "CDR XSL/T Filtering"
        opts = {
            "banner": title,
            "subtitle": "QC Filter Sets",
            "css": ".report a { padding-left: 2px; padding-right: 2px; }"
        }
        report = cdrcgi.Report(title, [table], **opts)
        report.send()

    def show_filtered_doc(self):
        "Filter the document and display the results."
        doc = self.filter_doc().replace("@@DOCID@@", self.cdr_id)
        text_type = "<?xml" in doc and "xml" or "html"
        cdrcgi.sendPage(unicode(doc, "utf-8"), text_type)

    def filter_and_validate(self):
        """
        Run the document through all the selected filters and then
        validate it against the specified DTD. Display a report
        showing all the warnings and errors.
        """
        title = "Validation results for %s" % self.cdr_id
        if "/" not in self.dtd and "\\" not in self.dtd:
            self.dtd = "%s\\%s" % (cdr.PDQDTDPATH, self.dtd)
        if not os.path.exists(self.dtd):
            cdrcgi.bail("%s not found" % repr(self.dtd.replace("\\", "/")))
        errors = cdrpub.Control.validate_doc(self.filter_doc(), self.dtd)
        if not errors and not self.warnings:
            title += " (passed)"
        columns = (
            cdrcgi.Report.Column("Type"),
            cdrcgi.Report.Column("Document"),
            cdrcgi.Report.Column("Line"),
            cdrcgi.Report.Column("Message")
        )
        rows = []
        if self.warnings:
            rows.append(("Warning", self.cdr_id, "N/A", self.warnings))
        for error in errors:
            rows.append((error.level_name, self.cdr_id, error.line,
                         error.message))
        if not rows:
            columns = [cdrcgi.Report.Column("Document is valid")]
        table = cdrcgi.Report.Table(columns, rows)
        report = cdrcgi.Report(title, [table])
        report.send()

    def filter_doc(self):
        "Run the document through all of the selected filters."
        parms = self.parms()
        response = cdr.filterDoc(self.session, self.filters, self.cdr_id,
                                 docVer=self.version, parm=self.parms())
        try:
            doc, self.warnings = response
            return doc
        except:
            cdrcgi.bail(response)

    def parms(self):
        "Pack up the parameters to be fed to the CDR filter module."
        parms = [
            ("insRevLevels",            "_".join(self.ins_levels)),
            ("delRevLevels",            self.del_levels and "Y" or "N"),
            ("DisplayComments",         self.comments),
            ("DisplayGlossaryTermList", self.glossary and "Y" or "N"),
            ("ShowStandardWording",     self.standard_wording and "Y" or "N"),
            ("displayBoard",            "_".join(self.boards)),
            ("displayAudience",         "_".join(self.audiences)),
            ("isPP",                    self.is_pp and "Y" or "N"),
            ("isQC",                    self.is_qc and "Y" or "N"),
            ("displayLOETermList",      self.loeref and "Y" or "N")]
        if self.vendor_or_qc:
            parms.append(("vendorOrQC", 'QC'))
        cdr.logwrite(repr(parms))
        return parms

    def check_filter(self, spec):
        """
        Verify that the filter spec is a real filter document or set
        on this tier's CDR server.
        """
        if spec.startswith("name:"):
            name = spec[5:]
            if name.upper() not in self.all_filters:
                cdrcgi.bail("%s is not a filter on the CDR %s server" %
                            (repr(name), self.TIER.name))
        elif spec.startswith("set:"):
            name = spec[4:]
            if name.upper() not in self.filter_sets:
                cdrcgi.bail("%s is not a filter set on the CDR %s server" %
                            (repr(name), self.TIER.name))
        else:
            digits = spec
            if spec.upper().startswith("CDR"):
                digits = spec[3:]
            if not digits or not digits.isdigit():
                cdrcgi.bail("%s is not a well-formed CDR ID" % repr(spec))
            try:
                cdr_id = cdr.normalize(spec)
                if cdr_id not in self.all_filter_ids:
                    cdrcgi.bail("%s is not a filter on the CDR %s server" %
                                (cdr_id, self.TIER.name))
            except Exception as e:
                cdrcgi.bail("%s is not a well-formed CDR ID" % repr(spec))

    @staticmethod
    def set_wanted(filter_set, filter_ids):
        """
        Determine whether we want to show this filter set.  If any filters
        are explicitly listed in the filter data entry fields, then we
        only want to show those filters which contain *all* of the filters
        so listed. Otherwise, show all the sets.
        """

        if not filter_ids:
            return True
        ids_in_set = set([cdr.exNormalize(m.id)[1]
                           for m in filter_set.members])
        if filter_ids - ids_in_set:
            return False
        return True

    @staticmethod
    def show_cache_warning(table, page):
        "If we're unable to refresh the filter set cache, let the user know."
        warning = table.user_data()
        if warning:
            page.add(page.B.P(warning, page.B.CLASS("error center")))

class ActionCell(cdrcgi.Report.Cell):
    "Populate a cell in the table with two buttons linked to filter tasks."
    def __init__(self, script, args):
        cdrcgi.Report.Cell.__init__(self, "")
        self.script = script
        self.args = args
    def to_td(self):
        return cdrcgi.Page.B.TD(self.make_button(), self.make_button(True))
    def make_button(self, validate=False):
        args = self.args
        if validate:
            label = "Validate"
            args += "&validate=Y"
        else:
            label = "Filter"
        url = "%s?%s" % (self.script, args)
        return cdrcgi.Page.B.A(cdrcgi.Page.B.BUTTON(label), href=url)
        return cdrcgi.Page.B.A(label, cdrcgi.Page.B.CLASS("button"), href=url)
        return cdrcgi.Page.B.BUTTON(label, type="submit",
                                    formaction=url)

if __name__ == "__main__":
    """
    Allow documentation and code-checking tools to import this without
    side effects.
    """
    Control().run()
