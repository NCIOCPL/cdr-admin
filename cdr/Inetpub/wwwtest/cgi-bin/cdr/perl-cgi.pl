#!/usr/bin/perl

#----------------------------------------------------------------------
#
# $Id: perl-cgi.pl,v 1.1 2006-05-04 14:17:51 bkline Exp $
#
# Template for Perl CGI programming; demonstrates returning a binary file.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
use CGI;
use Archive::Zip;
use strict;

#----------------------------------------------------------------------
# Driver.
#----------------------------------------------------------------------
sub main {
    binmode STDOUT;
    my $cgi     = new CGI;
    my $cutoff  = $cgi->param('cutoff');
    my $zipfile = createZipfile($cutoff);
    print "Content-type: application/zip; name=\"test.zip\"\r\n\r\n";
    $zipfile->writeToFileHandle(*STDOUT, 0);
}

#----------------------------------------------------------------------
# Error reporting.
#----------------------------------------------------------------------
sub bail {
    my $err = shift;
    print "Content-type: text/html\r\n\r\n";
    print <<EOT;
<html>
 <head>
  <title>Error</title>
 </head>
 <body>
  <h1>Error</h1>
  <p>$err</p>
 </body>
</html>
EOT
    exit 1;
}

#----------------------------------------------------------------------
# Create and populate a zipfile object.
#----------------------------------------------------------------------
sub createZipfile {
    my $cutoff   = shift;
    my $zip      = Archive::Zip->new();
    my $manifest = "";
    my $trials   = collectTrials();
    foreach my $trial (@$trials) {
        $manifest .= "$trial->{id}\t$trial->{status}\n";
        if (needToExport($trial, $cutoff)) {
            $zip->addString(makeDummyXml($trial->{id}), $trial->{id} . '.xml');
        }
    }
    $zip->addString($manifest, "manifest.txt");
    return $zip;
}

#----------------------------------------------------------------------
# Pretend we're gathering up the list of all the trials in our database.
#----------------------------------------------------------------------
sub collectTrials {
    [
     { "id" => "COG-1234", "status" => "Approved", "changed" => "2005-01-11" },
     { "id" => "COG-2345", "status" => "Active",   "changed" => "2005-02-01" },
     { "id" => "COG-3456", "status" => "Closed",   "changed" => "2004-12-09" },
     { "id" => "COG-4567", "status" => "Active",   "changed" => "2005-01-28" },
     { "id" => "COG-5678", "status" => "Approved", "changed" => "2003-08-14" },
     { "id" => "COG-6789", "status" => "Approved", "changed" => "2004-10-03" },
     { "id" => "COG-7890", "status" => "Active",   "changed" => "2004-12-12" }
    ];
}

#----------------------------------------------------------------------
# Determine whether we want to include this trial's XML information.
#----------------------------------------------------------------------
sub needToExport {
    my $trial  = shift;
    my $cutoff = shift;
    if ($trial->{id} eq "xxCOG-5678") {
        bail("cutoff: '$cutoff'; changed: '$trial->{changed}'");
    }
    if ($trial->{status} ne 'Active' && $trial->{status} ne 'Approved') {
        0; # Out of scope
    }
    elsif ($cutoff && $cutoff gt $trial->{changed}) {
        0; # Already exported
    }
    else {
        1; # OK
    }
}

#----------------------------------------------------------------------
# Create a (dummy) XML file.
#----------------------------------------------------------------------
sub makeDummyXml {
    my $id = shift;
    return "<?xml version='1.0' encoding='utf-8'?>\n<trial id='$id'/>\n";
}

main;
