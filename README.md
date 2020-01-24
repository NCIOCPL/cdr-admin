# CDR Administrative Interface

The administration of the CDR is largely performed through a web-based
interface, for which the login page is at
[https://cdr.cancer.gov](https://cdr.cancer.gov) (on the lower tiers
"cdr" is replaced by "cdr-dev" or "cdr-qa" or "cdr-stage" as
appropriate for the specific tier). Users can also reach this
interface with a toolbar button in the desktop XMetaL CDR editing
application.

The scripts (including Javascript) and CSS for the CDR Admin interface
are in this repository.

Subdirectories contain:

* [admin CGI scripts](Inetpub/wwwroot/cgi-bin/cdr)
* [secure login scripts](Inetpub/wwwroot/cgi-bin/secure)
* [client-side scripting](Inetpub/wwwroot/js)
* [style sheets](Inetpub/wwwroot/stylesheets)
* [images](Inetpub/wwwroot/images)

Common functionality is factored out into common Python modules, stored
in a [separate repository](https://github.com/NCIOCPL/cdr-lib).
