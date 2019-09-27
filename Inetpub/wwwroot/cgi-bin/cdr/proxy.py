#----------------------------------------------------------------------
# Passthrough to get resources from unsecured URLs.
# JIRA::OCECDR-3588
#----------------------------------------------------------------------
import cgi
import cdr
import os
import requests
import urllib.parse
import re
import sys
import datetime

# TODO: Get Acquia to fix their broken certificates.
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

CHUNK = 32000

#----------------------------------------------------------------------
# Record errors.
#----------------------------------------------------------------------
def log(url, problem):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(f"{cdr.DEFAULT_LOGDIR}/proxy.log", "a") as fp:
            fp.write(f"{now} {url!r}: {problem}\n")
    except:
        pass

#----------------------------------------------------------------------
# It turns out that Internet Explorer (or at least the most recent
# versions of IE) will not wait for us to parse nvcg.css. So I had to
# abandon the use of the csstools module and do the work with regular
# expressions. Not as robust, but it works (for now).
#
# Code from my prototype test of the new approach:
#   css = open("nvcg.css").read()
#   print re.sub("url[(]([^)]+)[)]", src_replacer, css)
#----------------------------------------------------------------------
def src_replacer(match):
    src = match.group(1).strip()
    src = src.strip("'\"")
    if src.startswith("data:"):
        return match.group(0)
    if src.startswith("https"):
        return match.group(0)
    if not src.startswith("http"):
        if src.startswith("/"):
            src = f"{absolute_base}/{src}"
        else:
            src = f"{relative_base}/{src}"
    return f'url("{proxy}?url={src}")'


#----------------------------------------------------------------------
# Relative URLs in proxied CSS files won't work. Proxy those, too.
# Probably wouldn't be hard to break this parsing with edge cases.
# 2015-04-20: took too long to parse nvcg.css with the cssutils
# package, so I'm falling back on regular expression. Will be even
# less robust, but at least it will work with IE.
#----------------------------------------------------------------------
def fix_css(original, url):
    try:
        return re.sub(r"url\s*\(([^)]+)\)", src_replacer, original)
    except Exception as e:
        log(url, e)
        return original

#----------------------------------------------------------------------
# Send the payload back through our own web server. Have to do this
# in slices of the bytes, because of a Windows bug:
# See https://bugs.python.org/issue11395.
#----------------------------------------------------------------------
def send(what, content_type=None):
    if content_type is None:
        content_type = "text/plain;charset=utf-8"
    header = f"Content-type: {content_type}\r\n\r\n"
    sys.stdout.buffer.write(header.encode("utf-8"))
    written = 0
    while written < len(what):
        portion = what[written:written+CHUNK]
        sys.stdout.buffer.write(portion)
        written += CHUNK
    sys.exit(0)

start = datetime.datetime.now()
fields = cgi.FieldStorage()
url = fields.getvalue("url")
try:
    response = requests.get(url, verify=False)
    code = response.status_code
    if code != 200:
        log(url, f"code: {code!r}")
        send("")
    payload = response.content
    content_type = None
    for header in response.headers:
        if header.lower().startswith("content-type"):
            content_type = response.headers.get(header).strip()
            break
    if isinstance(content_type, str) and "css" in content_type:
        proxy = "/cgi-bin/cdr/proxy.py"
        parsed_url = urllib.parse.urlparse(url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        path = parsed_url.path
        path, resource = os.path.split(path)
        absolute_base = f"{scheme}://{netloc}"
        relative_base = absolute_base + path
        payload = fix_css(payload, url)
    elapsed = datetime.datetime.now() - start
    log(url, f"elapsed: {elapsed}")
except Exception as e:
    log(url, e)
    send("")
send(payload, content_type)
