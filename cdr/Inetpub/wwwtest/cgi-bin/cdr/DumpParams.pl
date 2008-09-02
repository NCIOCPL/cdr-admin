#!/usr/bin/perl
use CGI;

$query = new CGI;
@keywords = $query->keywords;
print "Content-type: text/html\n\n";
print "<H2>Current Values</H2> $query\n<HR>\n";
#print "<HTML><HEAD><TITLE>Parameter list</TITLE></HEAD><BODY>\n";
#foreach $keyword (@keywords) { print "$keyword<BR>\n"; }
print $query->Dump;
print "</BODY></HTML>\n";
# @values = $query->param('foo');
