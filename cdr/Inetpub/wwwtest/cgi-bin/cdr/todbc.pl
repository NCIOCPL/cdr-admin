#!/usr/bin/perl -w
use DBI;
#use Spreadsheet::WriteExcel;

# take care of DOS silliness.
#binmode(STDOUT);

my $dsn = "ODBC:cdr";
my $uid = "cdr";
my $pwd = "***REMOVED***";
#DBI->trace(2);
my $dbh = DBI->connect("DBI:$dsn", "$uid", "$pwd") ||
       die "Error connecting [$DBI::errstr]\n";
my $basePath = "/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/";
my $protIdPath = "/InScopeProtocol/ProtocolIDs/PrimaryID/IDString";
my $leadOrgPath = $basePath . "LeadOrganizationID/\@cdr:ref";
my $orgNamePath = "/Organization/OrganizationNameInformation/OfficialName" .
                  "/Name";
my $orgStatusPath = $basePath . "LeadOrgProtocolStatuses/CurrentOrgStatus/" .
                             "StatusName";
my $query = sprintf("
    SELECT TOP 50 prot_id.value,
                  prot_id.doc_id,
                  org_name.value,
                  org_status.value
             FROM query_term prot_id
             JOIN query_term lead_org
               ON lead_org.doc_id = prot_id.doc_id
             JOIN query_term org_name
               ON org_name.doc_id = lead_org.int_val
             JOIN query_term org_status
               ON org_status.doc_id = prot_id.doc_id
              AND LEFT(org_status.node_loc, 8) = LEFT(lead_org.node_loc, 8)
            WHERE prot_id.path = '%s'
              AND lead_org.path = '%s'
              AND org_name.path = '%s'
              AND org_status.path = '%s'", $protIdPath,
                                           $leadOrgPath,
                                           $orgNamePath,
                                           $orgStatusPath);
print "$query\n";
$sth = $dbh->prepare($query) or die "$DBI::errstr";
$sth->execute() or die "$DBI::errstr";

#print "Content-type: application/vnd.ms-excel\r\n\r\n";
#print "Content-type: application/x-msexcel\r\n\r\n";
# Create a new Excel workbook
#my $workbook = Spreadsheet::WriteExcel->new("-");
#my $ws = $workbook->addworksheet("Sample CDR Worksheet");
#my $format = $workbook->addformat();
#$format->set_bold();
#$format->set_color('blue');
#$format->set_align('center');
#$ws->write(0, 0, "Prot ID", $format);
#$ws->write(0, 1, "Doc ID", $format);
#$ws->write(0, 2, "Organization Name", $format);
#$ws->write(0, 3, "Organization Protocol Status", $format);
#my $row = 1;
while (@results = $sth->fetchrow) {
    print "$results[0]\t$results[1]\t$results[2]\t$results[3]\n";
}
#my $val = shift @results;
#$val = "[null]" unless defined $val;
#printf "%10s: %s\n", $field_name, $val;
$sth->finish;
$dbh->disconnect();
#$workbook->close();
#$dbh->commit;
