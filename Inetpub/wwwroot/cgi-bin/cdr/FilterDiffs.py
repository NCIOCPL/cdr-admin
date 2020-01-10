#!/usr/bin/env python

"""Compare filters between the current tier and the production tier.
"""

from sys import stdout
from difflib import unified_diff
import cgi
from lxml import etree
import json
import requests
import cdr
import cdrcgi
from cdrapi import db
from cdrapi.settings import Tier

class Control:
    """Wrap the processing in a single namespace."""

    URL = "https://cdr.cancer.gov/cgi-bin/cdr/ShowDocXml.py?DocId={}"
    CACHED_PROD_FILTERS = f"{cdr.BASEDIR}/Filters/prod-filters.json"

    def run(self):
        """Run the report (top-level entry point)."""

        if cdr.isProdHost():
            cdrcgi.bail("Can't compare the production server to itself")
        lines = []
        for name in sorted(self.filter_names, key=str.lower):
            if name not in self.local_filters:
                lines += self.only_on(name, "PROD")
            elif name not in self.prod_filters:
                lines += self.only_on(name, self.tier.name)
            else:
                lines += self.compare(name)
        if not lines:
            lines = [f"Filters on {self.tier.name} and PROD are identical"]
        lines = "\n".join(lines) + "\n"
        stdout.buffer.write(b"Content-type: text/plain; charset=utf-8\n\n")
        stdout.buffer.write(lines.encode("utf-8"))

    def compare(self, name):
        """Run a diff between the local and production copies of a filter."""

        prod = self.normalize(self.prod_filters[name])
        local = self.normalize(self.local_filters[name])
        opts = dict(lineterm="")
        lines = list(unified_diff(prod, local, "PROD", self.tier.name, **opts))
        if lines:
            return self.filter_banner(name) + lines
        return []

    def filter_banner(self, filter_name):
        """Put the filter name at the top of a message or diff report"""
        return ["=" * len(filter_name), filter_name, "=" * len(filter_name)]

    def only_on(self, filter_name, tier_name):
        """Create a message to show a filter missing from one or the other."""
        return self.filter_banner(filter_name) + [f"Only on {tier_name}", ""]

    @property
    def filter_names(self):
        """Names of all filters, including those on one tier only."""

        if not hasattr(self, "_filter_names"):
            names =  set(self.local_filters) | set(self.prod_filters)
            self._filter_names = names
        return self._filter_names

    @property
    def tier(self):
        """Name of the local tier."""

        if not hasattr(self, "_tier"):
            self._tier = Tier()
        return self._tier

    @property
    def fields(self):
        """CGI parameters."""

        if not hasattr(self, "_fields"):
            self._fields = cgi.FieldStorage()
        return self._fields

    @property
    def local_filters(self):
        """Dictionary of local filters, indexed by title."""

        if not hasattr(self, "_local_filters"):
            self._local_filters = {}
            query = db.Query("document d", "d.title", "d.xml")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'Filter'")
            for title, xml in query.execute().fetchall():
                self._local_filters[title] = xml
        return self._local_filters

    @property
    def prod_filters(self):
        """Dictionary of PROD filters, indexed by title."""

        if not hasattr(self, "_prod_filters"):
            if not self.refresh_cache:
                try:
                    with open(self.CACHED_PROD_FILTERS) as fp:
                        self._prod_filters = json.load(fp)
                    return self._prod_filters
                except Exception as e:
                    self.logger.warning("Failure loading from cache: %s", e)
            self._prod_filters = {}
            for filt in cdr.getFilters("guest", tier="PROD"):
                url = self.URL.format(filt.id)
                response = requests.get(url)
                if response.status_code != requests.codes.ok:
                    msg = f"{url}: {response.status_code} ({response.reason})"
                    cdrcgi.bail(msg)
                self._prod_filters[filt.name] = response.text
            try:
                with open(self.CACHED_PROD_FILTERS, "w") as fp:
                    json.dump(self._prod_filters, fp)
            except:
                pass
        return self._prod_filters

    @property
    def refresh_cache(self):
        """Flag indicating whether we need to get fresh filters from PROD."""

        if not hasattr(self, "_refresh_cache"):
            self._refresh_cache = False
            if self.fields.getvalue("refresh-cache"):
                self._refresh_cache = True
        return self._refresh_cache

    @staticmethod
    def normalize(xml):
        """Eliminate irrelevant differeneces."""
        node = etree.fromstring(xml.encode("utf-8"))
        xml = etree.tostring(node, encoding="utf-8").decode("utf-8")
        return (xml.strip().replace("\r", "") + "\n").splitlines()


Control().run()
