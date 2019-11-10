#!/usr/bin/env python

"""Pass through resources from unsecured URLs.
"""

from cdrcgi import Controller, sendPage
from os import path
from re import compile
from sys import stdout
import requests
from urllib.parse import urlparse

# TODO: Get Acquia to fix their broken certificates.
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class Control(Controller):

    CHUNK = 32000
    LOGNAME = "proxy"
    PATTERN = compile(r"url\s*\(([^)]+)\)")
    PROXY = "/cgi-bin/cdr/proxy.py"

    def run(self):
        """Take over routing, as everything about this script is custom."""

        self.logger.info("proxying %s", self.url)
        if self.response.status_code != 200:
            self.logger.error("Failure reason: %s", self.response.reason)
            raise Exception(f"Failed with status {self.response.status_code}")
        self.logger.info("elapsed: %s", self.elapsed)
        self.send()

    def send(self):
        """Send the payload back through our own web server.

        Have to do this in slices of the bytes, because of a Windows bug.
        See https://bugs.python.org/issue11395.
        """

        header = f"Content-type: {self.content_type}\r\n\r\n"
        stdout.buffer.write(header.encode("utf-8"))
        written = 0
        while written < len(self.payload):
            portion = self.payload[written:written+self.CHUNK]
            stdout.buffer.write(portion)
            written += self.CHUNK

    def callback(self, match):
        """Replace a relative URLs in CSS rules with proxy URLs.

        It turns out that Internet Explorer (or at least the most
        recent versions of IE) will not wait for us to parse
        nvcg.css. So I had to abandon the use of the csstools module
        and do the work with regular expressions. Not as robust, but
        it works (for now).

        Code from my prototype test of the new approach:
            css = open("nvcg.css").read()
            print re.sub("url[(]([^)]+)[)]", callback, css)

        Pass:
            match - what the regular expression found

        Return:
            original URL if no proxying needed; otherwise a modified
            URL directed at this script
        """

        src = match.group(1).strip().strip("'\"")
        if src.startswith("data:"):
            return match.group(0)
        if src.startswith("https"):
            return match.group(0)
        if not src.startswith("http"):
            if src.startswith("/"):
                src = f"{self.absolute_base}/{src}"
            else:
                src = f"{self.relative_base}/{src}"
        return f'url("{self.PROXY}?url={src}")'

    @property
    def absolute_base(self):
        """Start of a URL to which we can attach an absolute path."""

        return f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"

    @property
    def content_type(self):
        """Turned around from the proxied source."""
        return self.response.headers.get("content-type", "text/plain")

    @property
    def parsed_url(self):
        """Access to the components of the url which we are proxying."""

        if not hasattr(self, "_parsed_url"):
            self._parsed_url = urlparse(self.url)
        return self._parsed_url

    @property
    def payload(self):
        """Bytes ready to be returned to the user's browser.

        Relative URLs in proxied CSS files won't work. Proxy those,
        too. Probably wouldn't be hard to break this parsing with
        edge cases.

        2015-04-20: took too long to parse nvcg.css with the cssutils
        package, so I'm falling back on a regular expression. Will be
        even less robust, but at least it will work with IE.
        """

        if not hasattr(self, "_payload"):
            self._payload = self.response.content
            if "css" in self.content_type:
                original = self._payload.decode("utf-8")
                modified = self.PATTERN.sub(self.callback, original)
                self._payload = modified.encode("utf-8")
        return self._payload

    @property
    def relative_base(self):
        """Start of a URL to which we can attach a relative path."""

        segments = path.split(self.parsed_url.path)
        return f"{self.absolute_base}{segments[0]}"

    @property
    def response(self):
        """What we get back from the URL we're proxying."""

        if not hasattr(self, "_response"):
            self._response = requests.get(self.url, verify=False)
        return self._response

    @property
    def url(self):
        """The resource we're tunneling."""

        if not hasattr(self, "_url"):
            self._url = self.fields.getvalue("url")
        return self._url


if __name__ == "__main__":
    """Don't invoke the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception:
        control.logger.exception("Failure")
        sendPage("", textType="plain")
