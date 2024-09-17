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

The following sections describe each of the available CGI administrative tools and reports.

## User Activity reports
### Audit Trail
Provides a list of all of the activity for a specific CDR document. Can be limited to the most recent N actions. The report's table has columns for the date and time of the action, the name of the user performing the action, and the name of the action (ADD DOCUMENT, MODIFY DOCUMENT, LOCK, UNLOCK).
### Current Sessions
Provides a table showing the active logins, including information about the account for each session, as well as when the session was initiated and when the last activity was performed for that session.
### Document Activity Report
Provides a table showing the audit trail activity for actions on CDR documents, showing when the activity was performed on which documents by which users. Can be filtered by user, document type, and/or date range.
### Inactivity Report
A tabular HTML report listing CDR documents which have been locked without any activity for a specified minimum amount of time (defaulting to 10 days). The following columns are displayed.
* Document ID
* Type
* User
* Checked Out
* Last Action
* Action Date
### Locked Documents
Shows the CDR documents which are locked by a specified user on the current tier. The user can specify whether the report should be generated as an HTML table or as an Excel workbook.
## Generic Tools
### Advanced Search
There is one interface for each of the CDR document types, with a customized search form populated with fields appropriate to each type, and a flag for controlling whether the criteria for a search will be ANDed together (narrowing to the intersection of documents which meet all of the criteria) or ORed together (expanding to the union of documents which meet any of the criteria). The report output consists of a list of CDR ID and title for each matching document, with a link to the QC report for each document. There is a variant report for Person documents, showing the location information for the persons found to facilitate distinguishing between persons with the same name. The Advanced Citation Search form also has fields for importing or updating CDR Citation documents from NLM's PubMed.
### Batch Status Report
A tabular HTML report showing the status of batch jobs. Can be filtered by job ID, job name, maximum job age, and/or job status.
### Date Last Modified Report
Report of all CDR documents of a specified document type modified within a given range of dates. An option for running the report for all document types is available. The user can choose between an HTML report or an Excel report.
### Display CDR Document XML
Shows the XML for a given version of a CDR document. The document can be identified by CDR ID or by title and document type. If a title fragment is entered and it matches more than one document, a cascading page is shown allowing the user to select one of the documents. The following options are available for specifying which version to display:
* the most recently saved XML (possibly not versioned)
* the most recently created version
* the most recently created publishable version
* a specific version by version number
* the filtered XML most recently sent to cancer.gov
### Documents Modified Report
An Excel spreadsheet showing the CDR ID, document title, number of the latest saved version, and whether that version has been marked as publishable, for all documents modified within a specified date range. The report can be run for one specific document type, or for all document types.
### Documents Modified Without a Publishable Version
An HTML tabular report showing documents which were most recently saved during a specified date range without creating a publishable version, with columns for the document ID, the date and time the latest publishable version was saved (if any), who performed that last save action, when that action was performed, and the date and time of the latest non-publishable version of the document (if any). The report can optionally be filtered by user and/or document type.
### Document Counts By Type Report
HTML tabular report of the number of CDR documents exported by the most recent publishing job by document type.
### Document Deletion
An HTML form for marking one or more CDR documents as "deleted" with an optional comment explaining the deletion. The affected documents are not actually removed from the database, but are assigned the `active_status` value of "D" which prevents the documents from showing up in reports and from being included in batch processing jobs. There is also a form which can be used to restore "deleted" documents, with fields for identifying which documents to restore, which status to restore them to ("Inactive" or "Active"), and what comment (if any) should be stored in the audit table for the restoration action.
### Document Version History
This heavily-used web report is typically launched from a toolbar button in XMetaL for the document in the currently active editing tab, but it can also be invoked directly from the CDR admin web menus. Two tables are displayed, a smaller one at the top of the page showing general information about the document (ID, type, title, who created the document, who modified the document most recently, and the dates of those actions), and a larger table showing each version on a separate table row (latest versions at the top), with the following columns:
* version number
* comments
* date/time the version was created
* user who created the version
* whether the version was validated (and if so whether it passed validation)
* whether the version was marked as publishable
* date and job ID of each of the publishing jobs which used the version
### External Map Failures Report
A report is provided for identifying values which have not been mapped in the external mapping table. The report can be customized by how long ago the values were entered in the table, which map usages should be included, and whether to include values marked as "unmappable." See **Edit External Maps** below under **System Tools**.
### Generate Spanish Spellcheck Files From Dictionary
This tool creates a Spanish dictionary file which can be installed in the XMetaL dictionary location on the network at `OCPL\_Cross\CDR\STEDMANS. The user specifies which glossary audience (patient or health professional) to use for generating the dictionary file.
### Get CDR Blob
Stream media blob over HTTP directly from the CDR database. We do this to avoid limitations imposed on memory usage within the CDR Server.
### Get CDR Image
Send JPEG version of a CDR image to the browser, possibly resized. Also used by Visuals Online.
### Get Report Workbook
Sends back a report created as an Excel workbook to the client. The report will have been stored in the file system.
### Help Pages
User, system, and operations help pages are provided. A landing page for each type of help shows a hierarchical table of contents with links to specific help pages. Those pages in turn link to other, related pages. The pages are maintained in the CDR as XML `Documentation` documents. The tables of contents for each of the sets of help pages are also maintained in the CDR as XML `DocumentationToC` documents.
### Invalid And Blocked Documents
An HTML report with two tables, one for invalid (but unblocked) CDR document of a specified document type, and a second for blocked documents of that type. Each table contains two columns: one for the document ID and the second for the document title.
### Last PDQ Data Partner Retrievals
A plain-text report showing one line for each s/FTP login account name with the date and time of the last access to the server from which PDQ data sets are served. The report is run from time to time by a developer at the request of NCI staff. It is only available on the CDR development server, because it is created from a backup of the s/FTP server logs which is only present on CDR DEV. Not included on the CDR administrative menus.
### Links To Document Report
A tabular HTML report identifying CDR documents which link to a specified document. The user can either enter the CDR ID for the linked document or the user can provide the title of that document (and optionally a document type). If the user enters a title string which matches the start of more than one document title (for that document type, if the user has selected a type), the user will be asked to select the document from a list of those which match. The user can also specify a fragment ID to further restrict the links which are reported to those which link to one specific element of the target document. The user can restrict the report to links from only a specified document type, or the user can include links from any document type. Finally, the user can exclude or include links from documents which have been blocked. Separate tables are created for each linking document type.
### New Document Counts
HTML tabular report showing statistics for CDR documents newly added during a specified date range by document type. The report can be run for a single document type, or for all document types, with a separate table for each type. Counts are provided for documents which are:
* published
* ready for publication
* ready for review
* valid
* unvalidated
* invalid
* malformed
### New Documents Detailed Report
An HTML tabular report showing information about CDR documents newly added during a specified date range by document type. The report can be run for a single document type, or for all document types, with a separate table for each type. Each document is represented by a row containing the following columns:
* CDR ID
* Document Title
* Created By
* Creation Date
* Latest Version Date
* Latest Version Saved By
* Publishable?
* Earlier Publishable Version?
### PCIB Status Report
This is a management report which is normally run by the scheduler on the 1st of every month, providing a variety of counts for the previous month regarding the number of documents published, updated, etc. An interface is provided for running the report independently of the scheduler, with fields for specifying a date range, which sections to include, whether to include individual documents, and if so, whether to include a column for the CDR IDs.
### PDQ Content Counts
An HTML tabular report showing the total number of documents for each of the following categories.
* PDQ English health-professional summaries
* PDQ Spanish health-professional summaries
* PDQ English patient summaries
* PDQ Spanish patient summaries
* English Consumer-Focused Content Modernization (CFCM) summaries
* Spanish Consumer-Focused Content Modernization (CFCM) summaries
* Drug information summaries
* NCI Dictionary of Cancer Terms in English
* NCI Dictionary of Cancer Terms in Spanish
* NCI Dictionary of Genetics Terms in English
* NCI Dictionary of Genetics Terms in Spanish
* NCI Drug Dictionary Terms
* English Biomedical Images and Animations
* Spanish Biomedical Images and Animations
### PDQ Summaries on Drupal
This tabular report, which can be generated as an HTML page or an Excel spreadsheet, shows the Cancer Information Summary and Drug Information Summary nodes on a Drupal CMS server for Cancer.gov. The report's table has columns for the CDR ID for the summary document from which the node was created, the summary title, the summary type (CIS or DIS) and the summary's language (English or Spanish). The report does not appear on the CDR Admin menus, but is instead invoked explicitly by the CDR development team to aid in analysis and troubleshooting. The report form has fields for selecting the output format, as well as for overriding the default CMS server DNS name for the current tier.
### Publish Preview
HTML pages showing how a CDR document will look on the NCI web site when it is published. This feature is available for cancer information summaries, drug information summaries, and dictionary entries. In addition to the script which prepares the document to be sent to the CMS for rendering, there is a proxy script which is used to manipulate resources which assume they are being served up from the NCI web site but are instead coming from the CDR server. There is a page with links for sample documents used to test the publish preview software. This was used heavily during transition to the current Drupal CMS but it no longer appears on the menus and is rarely used now.
### Publishing Job Creation
This interface allows an authorized user to initiate a publishing job outside the CDR Scheduler, using a series of cascading forms in which the user first selects the publishing system ("Primary" or "QC Filter Sets"), then the publishing subset (for example, "Hotfix-Export"), and finally the options to be used for this specific job. When the options have been submitted the job is created and assigned a job number, with a link to the job status page displayed so the user can track its progress. The options appearing on the third form are dynamically derived from the publishing control document for the selected publishing system. When the job completes, a link to the status page for the job is email to the user.
### Publishing Job Statistics
A tabular HTML report showing counts for each document type for a specified date range (defaulting to the previous week). The following columns are included in the report's table.
- **Doc Type** (for example, DrugInformationSummary)
- **Re-Added** This count includes documents that existed on Cancer.gov, had been removed and added again.
- **New** This count includes documents that are new and never existed on Cancer.gov before.
- **Updated** This count includes documents that have been updated on Cancer.gov. If a document has been added and updated during the specified time period it is only counted as a new document.
- **Updated\*** This count also includes documents that have been updated on Cancer.gov. If a document has been added and updated during the specified time period it is counted twice, once as a new document and once as an updated document.
- **Removed** This number includes documents that have been removed from Cancer.gov.
- **Total** This number sums up all columns (except for the column Updated*) to only count a document once per time frame specified.

A key explaining these columns is displayed above the report table.
### Publishing Status Report
With no parameters this report presents a form for specifying the date range for the publishing jobs whose statuses should be reported, defaulting to the most recent week. The form contains a field for optionally filtering by job type. When the form is submitted, a tabular HTML report is displayed containing a row for each job in the specified date range, ordered by job date and time, with the most recent jobs first. The report columns are
- Job ID
- Job Type
- Job Status
- Job Start
- Job Finish
- Docs With Errors
- Docs With Warnings
- Total Docs

The job ID links to a page which has extensive information about the job in several tables, including a table with general information about the job (system, subset, user, output location, dates of start and completion, status, messages, count of total documents, and a link to the corresponding paired export or push job), a table for all of the job's parameters, and a table showing statistics for the documents of each type published by the job (or, if the job contains few enough documents, detailed information about each document published by the job).
### QC Reports
A customized report is available for each CDR document type, showing all of the information in the document formatted for quality control review. In some cases (most notably for Summary documents) a large number of options are available for controlling how that information is displayed (for example, whether redline/strikeout formatting or bold/underlining is used to reflect editing markup). XSL/T filters are used to generate the HTML for these reports.
### Report Template
A template used for creating a new report, demonstrating how to use the `Controller` class from the `cdrcgi` module, as well as the supporting `Reporter` class (with the nested `Table` and `Cell` classes). Also provides an illustration of building and executing a SQL query using the `Query` class.
### Republish CDR Documents
This page can be used to request re-publishing of CDR documents which have already been sent to Cancer.gov, in a way which bypasses the optimization which normally prevents pushing of an unchanged document to the Cancer.gov web site.

The user may enter one or more CDR Document IDs, and/or one or more publishing Job IDs. Separate multiple ID values with spaces. The user may also select a document type. If the user selects a document type it is possible to indicate that all publishable documents of that type are to be included; otherwise, only those documents which are already in the `pub_proc_cg` table will be published. If a document type is not selected this flag is ignored. The user may also indicate that in addition to those documents selected for the document IDs, job IDs, and document type provided, the new publishing job should also identify and include documents which are the target of links from the base set of documents to be published, and are not already on Cancer.gov. Finally, when specifying one or more job IDs it is possible to indicate that only documents from those jobs marked as 'Failed' are to be included. If no job IDs are entered, this flag is ignored.

An export job will be created for generating the output suitable for publishing. This job, if successful, will in turn create a second job for pushing the exported jobs to Cancer.gov.

The user may optionally add an Email Address to which status notifications for the progress of the new publishing jobs will be sent, with links to pages with additional information about the status for the jobs.
### Show Global Change Test Results
Shows the results of a test-mode global change. The user selects a global change test job from the list presented on the landing page. This leads to a tabular listing of each of the documents processed by the test job, with columns for the document's CDR ID, the version processed, the size in bytes of the transformed document, the size in bytes of the report of differences between the transformed document and the document before transformation, and links to each of the versions of the document's pre-transformation XML, post-transformation XML, differences report, and (if any) error report. This table can be sorted by size of diff report (in descending order), document ID (in ascending order), or document size (in descending order).
### Show Schema
Sends the raw XML for a CDR XSD validation schema to the browser. A menu is displayed if a schema document ID is not already provided.
### SQL Queries
This page provides read-only access to the CDR database, with a form for submitting SQL SELECT queries to be generated as HTML tables, Excel spreadsheets, or serialized JSON output. Users can name and save queries for future use, and this facility is used frequently for generating ad-hoc reports or finding problem documents.
### Unblock Document
Utility for making a blocked document active again. The user enters the CDR ID of a blocked document on the form, and the document is unblocked, after which the form is re-drawn and the unblocking action is reported.
### Unchanged Documents Report
A tabular HTML report showing documents which have not been updated for a specified amount of time. The table contains columns for the document ID, the document title, and the date the document was last saved. The report form has fields for specifying the age of documents to be included (defaulting to not saved for a year), the document type (default is all types) and the maximum number of documents to show (default 1000). The documents are sorted by title, and then by ID for documents which share the same title.
### URL Check
Reports on bloken links found in documents of a specified type (or optionally for a single CDR document). The report is queued by default as a batch processing job, in order to avoid the risk of taking so long that the report job exceeds the timeout limit and is killed. There are a number of miscellaneous options, including the option to perform a scaled-down version of the report without going through the batch job mechanism, in order to facilitate testing the report's software. There is a variant of this report which instead of looking for broken links reports on mismatches between the titles of the linked documents and the titles displayed with the links.
### URL List Report
This report originated as a series of stored SQL queries which the users asked to be incorporated into a report available on the CDR Admin menus. The user chooses an HTML report or an Excel spreadsheet, and selects one of the following document types:
* Citation
* Documentation
* DrugInformationSummary
* GlossaryTermConcept
* Media
* MiscellaneousDocument
* Summary

The report table has columns for the document ID, the document title, the URL, the display text (if available), and the source title (if available). There are different custom SQL queries for each document type, to accomodate the varying structures in which the URLs are stored.
### XMetaL CDR Icons
This HTML report shows the available icons the users can select for association with custom XMetaL commands.
## Citation Reports
### Citations Linked From Summaries
Generates an Excel report of all links to CDR Citation documents from CDR Summary documents. The full report generally takes about an hour or more to generate. When the report is ready an email notification will be sent to the address(es) provided, with a link to the Excel report. For testing the user can choose a quick version of the report, for which the user can specify the maximum number of Citation documents to be included, and/or the maximum number of seconds for collecting the information to be included in the report.
### New Citations
An HTML tabular report showing CDR Citation documents created during a specified date range (defaulting to the previous week). The Report table contains the following columns.
* CDR ID
* Document Title
* Created By
* Creation Date
* Last Version Publishable?
* PMID (with link to PubMed)
### Unverified Citations
A tabulary HTML report showing all of the CDR Citation document for which the *Verified* element is set to "No." The report's table contains columns for the document ID, the formatted bibliographic citation, and the comments pulled from the Citation document. The report uses the filters which prepare a Citation document for its QC report. The report is ordered by CDR document ID, oldest documents appearing first.
### Update Pre-Medline Citations
This script updates pre-Medline citations that have had their statuses changed since they were last imported or updated. It then generates an HTML report showing how many pre-Medline Citation documents were examined, and how many were changed. A table is displayed with a row for each changed Citation document, with columns for the PubMed ID, the CDR ID, the previous status, the new status, and a Notes column showing "updated," "failed," or "missing."
## Drug Reports
### DIS Comprehensive Review Dates Report
HTML or Excel report listing CDR Drug Information Summary documents with the date the document received a comprehensive review. Options are available for controlling whether a column for the CDR ID is to be included for each drug document, whether non-publishable documents should also be included, whether only single-agent drugs or combination drugs should be displayed, and whether all review dates should be shown or just the date of the most recent review. At the current time, no DIS documents have more than one comprehensive review recorded, so the usefulness of the last option is questionable.
### DIS Date Last Modified Report
An entended version of the general *Date Last Modified* report, this report also shows the date of the last time the document was saved, whether or not the user indicated that a non-trivial change was made to the document. This report also indicates who last saved the document, as well as whether the most recent version of the document was marked as publishable. The CDR ID in the first column provides a link to the *Document Version History* report for the document. Finally, the user can specify whether the date range filtering for the report should be applied to the "system" date (when the document was last saved) or the "user" date (when a user indicated that a non-trivial change had been made to the document).
### DIS Report By Drug Type
Displays a table showing the CDR ID, the preferred name for the drug, the drug type(s), and whether the Drug document has at least one publishable version, for all CDR drug term documents matching the one or more drug types selected by the user for the report. The report can be generated as an HTML web page or and Excel workbook.
### DIS Lists
An HTML tabular report showing the CDR Drug Information Summary documents, with columns for the CDR ID, title, drug type(s), whether approval of the drug is/was accelerated, and optionally whether the drug has been approved for use with children. There are two tables in the report, one for single agent drugs, and one for drug combinations.
### DIS Processing Status Report
Tabular report showing detailed information about the current processing and publication status of the CDR Drug Information Summary documents. The report can be optionally narrowed to specific statuses and/or to statuses entered during a specified date range. The report is available in both HTML and Excel formats.
### DIS Type of Change Report
This HTML or Excel report provides information about the changes made to one or more selected CDR Drug Information Summary documents. There are two types available for this report. The default is for the most recent changes for each category of change, and the other type is for an historical report which shows all changes for a specified date range. There are several options which can be used to customize the report, including whether separate tables show be created for each type of change, which types of change to include, and whether comments should be displayed. To run this report for multiple drug information summaries, the user chooses 'By CDR ID' under the Selection Method block and enters multiple CDR IDs separated by a comma. To generate the report for all drug information summaries, the user can run the ad-hoc query 'DIS CDR IDs for Type of Change Report' on the *CDR Stored Database Queries* page, and copy and paste the complete set of CDR IDs into the CDR ID field.
### DIS With Markup Report
This HTML tabular report lists all CDR Drug Information Summary documents with revision markup (Insertion and/or Deletion elements) for any of the specified markup levels (for example, "Approved" or "Proposed"), showing the document's CDR ID (linked to the document's QC report), title, and count of markup elements with each markup level.
### Drug Description Report
This HTML report displays the following information for each CDR Drug Information Summary document selected for the report:
* CDR ID (links to the document's QC report)
* Drug Name
* Drug Type(s)
* Accelerated Approval
* Approved for Children
* Description
* Summary

The following methods of filtering are available for the report:
* by drug name (one or more selections from a list of names)
* by date of last publishable version (using fields for a date range)
* by drug reference type (choosing one of "NCI," "FDA," or "NLM")
* by FDA approval information (checkboxes for "Accelerated approval" and "Approved in children"). For all filtering methods the user can further narrow the report by selecting one or more drug type.
### Drug Indications Report
A tabular HTML report showing the approved indications (that is, the diseases for which use of a given drug has been approved for treatment) for drugs represented by CDR Drug Information Summary documents. There are two organizations available for the report. The default organization shows a row for each "indication" with a list of all the drugs approved for use with that disease. The alternate organization has a row for each drug, with a list of all diseases for which use of the drug has been approved. The user can suppress or enable display of brand names along with the preferred drug name. It is also possible to filter the report to include only selected diseases. There is also a stripped-down version of the report which simply lists the diseases for which drugs have been approved, without listing the drugs at all.
### Elements Included in DIS Documents
Displays a list of CDR `DrugInformationSummary` documents, with counts of how many of the following elements are found in each document:
* Comment
* EmbeddedVideo
* MediaLink
* MiscellaneousDocLink
* StandardWording
* SummaryModuleLink
* Table
## Glossary Reports
### Concepts By Definition Status
Tabular HTML report listing GlossaryTermConcept documents having a specified definition status, with columns for the CDR document ID, the term name and pronunciation, definition, and definition resources, as well as optional columns for pronunciation resources and QC notes. The report can be optionally filtered by when the documents entered the specified state (using a date range). The definition status and audience fields on the report form are required.
### Concepts By Type
Tabular HTML report listing GlossaryTermConcept documents having a specified term type. The report form has required fields for the term type, definition status, and audience. It is also possible to further restrict the report by term name fragment or a string appearing in the definition text. The report table contains columns for the CDR of the concept document, the term names, and the definitions, with placeholder substitutions highlighted. By default only English term names and definitions, but there is an option for also including Spanish term names and definitions.
### Full Concept QC Report
A comprehensive HTML QC report for a GlossaryTermConcept document showing all of the information in the document, including definitions, term names (with pronunciation and audio links), images, status, comments, term types, processing dates, and related information. The form allows for selecting the concept by concept document ID, term name document ID, or term name string. An field is provided on the form for controlling whether the English and Spanish information is provided side-by-side, or stacked with the Spanish information below the English information.
### Glossary Keyword Search Report
Tabular report of glossary terms which contain a specified word or phrase in the term name or definition. The table contains columns for the concept document ID, the term name document ID, the term names, and the definitions, with the matches highlighted in the name and definition columns. The report can optionally be filtered by language and/or audience. Both HTML and Excel versions of the report are available.
### Glossary Processing Status Report
A tabular HTML report showing CDR GlossaryTermConcept and GlossaryTermName documents having the selected processing status. There are required fields for narrowing the report to a specific language and audience. There is also a pair of radio buttons with which the user controls whether the report only shows documents with the selected status, or also include linked glossary documents with other statuses. The second option causes the report to include glossary term concept documents which do not have the selected status but are linked by at least one glossary term name document which does have that status. It also causes the inclusion of glossary term name documents which do not have the selected status but whose concept document has that status.
### Glossary Term Phrases Report
A tabular HTML report listing all summaries in the selected language (English or Spanish) which contain a phrase matching a specified glossary term, with columns for the matching phrases found, the summary document title and ID, and the title of the section in which the matching phrase was found. The report can optionally be narrowed to only on audience (patients or health professionals) and at least one email address must be provided, because the report takes a considerable amount of time to run and is therefore run as a batch job, with a link to the generated report emailed to the address(es) provided.
### Glossary Terms for Health Professionals Report
Tabular HTML report of CDR GlossaryTermConcept documents containing definitions whose audience is health professionals, with columns for the CDR document ID, the term names (optionally with pronunciations), and the definitions (with placeholder substitutions highlighted). The report can be filtered by date of the document statuses, using a date range. An option is available for including blocked terms, which are excluded by default. The form requires that the user select between concepts assigned to the Genetics dictionary or concepts assigned to no dictionary. In the latter case, an option is provided for including level-of-evidence terms, which are excluded by default. A scaled-down version of the report is available, showing only a column for the term names.
### Links To Glossary Terms
A tabular HTML report showing all the links to a given CDR GlossaryTermName document. The document can be selected by CDR ID or term name. The report contains multiple tables: one at the top showing the term name and source, and one table for each document type of which at least one document links to the selected term name document. Those per-type tables have columns for the linking document's ID, its title, the linking element tag name, and the fragment ID of that element, if any.
### Modified Concepts
Excel report showing GlossaryTermConcept documents modified during a specified date range, with columns for the CDR ID, date last modified, whether the document is publishable, when any term name document linked to the concept was first published, and the last comment for the language and audience selected on the report form.
### Modified Term Names
An Excel report showing GlossaryTermName documents for which a new version was created during a specified date range. If more than one version of a name document was created during the date range, the latest of those versions is used. The report can optionally be filtered by term name status or concept definition audience. A required language field determines whether that filtering uses the English or the Spanish statuses/definitions, as well as which names and comments are displayed by the report. The following columns are present in the report table:
- CDR ID of the term name document
- term name for the selected language
- date last modified
- whether the version is publishable
- when the term document was first published
- the last comment entered for the selected language
- date the last publishable version of the document was created
### Newly Published Glossary Terms
An Excel report of GlossaryTermName documents first published during a specified date range. The report can optionally be narrowed by audience, language, and/or dictionary. The following columns are contained in the report table:
* CDR ID
* Term Name (English)
* Term Name(s) (Spanish)
* Date First Published
### Pronunciation By Term Stem Report
HTML tabular report with columns for CDR Document ID, the term name, the pronunciation, the pronunciation resource, and comments. GlossaryTermName documents whose term names contain a specified substring are included on the report. It is also possible to filter by pronunciations containing a specifed substring. These two filtering methods can be combined.
### Pronunciation Recordings Tracking Report
An Excel report of the audio pronunciation recordings made for glossary terms during a specified date range, with columns identifying the CDR Media document (ID and title), the glossary terms for which the pronunciations were made, the processing status (with date), comments, publishability, and dates of publication (first and last) and modification (most recent). The report can be filtered by language (English or Spanish). This is a batch report, with a link emailed to the user, since it takes so long to generate.
## Media Document Reports
### Board Meeting Recordings Tracking Report
An Excel report for the Media documents used for the audio recordings of the PDQ board meetings within a given date range, with colums for the CDR document ID and title, the recording's encoding (generally MP3) and date of creation, the date of the last version, whether that version is publishable, and any comments.
### Image Demographic Information Report
A tabular HTML report of demographic information for people shown in images stored with CDR Media documents. The table contains columns for document ID, image title, demographic information (age, sex, race, skin tone, and ethnicity), and a link to the QC report for the Media document. The report can be filtered by narrowing to images having specific demographic characteristics, first publication within a specified date range, audience, language, and/or diagnosis associated with the image. If both languages (English and Spanish) are included for the report (the default) then each column will appear twice, once for English, and once for Spanish. In addition to the common filtering described above, the user identifies which images are used to form the base set to be so filtered using one of the following methods:
* by CDR ID of the Media document
* by image title (wildcards supported)
* by image category (*e.g.*, anatomy or treatment); multiple selections are allowed
* by CDR ID of the Summary document linking to the Media documents
* by title of the Summary document linking to the Media documents (wildcards supported)
* by PDQ board for the Summary documents linking to the Media documents (multiple selections are allowed)
* by type of Summary documents (*e.g.*, Screening) linking to the Media documents (multiple selections are allowed)

For the last four selection methods (those identifying Summaries linking to Media image documents), additional columns identifying the linking Summary documents are included in the report's table, and an option is available to include Summary documents which can only be used as modules, which are excluded by default.

When the filtering criteria selects both languages for inclusion, and the selection methods just described select a Media document for only one language, the corresponding Media document for the other language is also included in the report.
### Image Keyword Search Report
Tabular report of CDR Media documents for images which contain at least one occurrence of any of the specified target phrases. The title, caption, description, and label blocks are examined to find such matches. The table contains columns for the Media document's CDR ID, title, and the block in which one or more matches were found, with those matches highlighted. A Media document will have multiple rows if matches were found in more than one block, with each block getting its own row. The report can be filtered by language, CDR ID, title, and/or processing status. The report can be produced as an HTML web page or as an Excel workbook.
### Image Media Processing Status Report
A tabular report showing CDR Media documents for images which currently have a given processing status. The table includes the following columns:
* CDR ID
* Media Title
* Diagnoses
* Processing Status
* Processing Status Date
* Proposed Summaries
* Proposed Glossary Terms
* Comments
* Last Version Publishable
* Published

The report can be optionally filtered to only include Media documents whose status date falls within a specified date range. Filtering is also available for restricting the report to those Media documents linked to one or more of specified diagnosis terms. The report can be generated as an HTML web page (the default) or an Excel workbook.
### Links To Media Documents
Tabular HTML report showing glossary terms, glossary definitions, and summaries which have links to CDR Media documents. A separate table is displayed for each of these three linking source types, and the report form allows the user to control which of these tables is shown. Only the linking documents are identified, with a column for the linking document ID and a column for the linking document title (or definition text in the case of the glossary definitions table). No information is shown for the Media link targets.
### Media In Summary Report
An HTML report showing the images linked by a selected CDR Summary document. The user selects a Summary document either by document ID or by title. By default, the report includes captions, descriptions, and labels for each image, but the user can elect to omit some or all of these elements. By default the report shows both the English Summary and the Spanish Summary with their images side-by-side, but the user can suppress this behavior, restricting the report only to the summary identified on the report form.
### Media Images Report
An HTML report of CDR Media documents for images. By default, English and Spanish versions of an image are displayed side-by-side, though for some flavors of the report it is possible to restrict the report so that images for only one language is displayed. Options are available for controlling what information is diplayed (whether to display captions, descriptions, and/or labels, and for which audiences). Three selection methods are available: by CDR ID, by Media document title, and by filtering on diagnoses, categories, and/or processing status date. The third (filtering) selection method is the one which allows the option of restricting the report to a single language, though the most common use of the report is for comparing the images for both languages (and in fact, even when the single-language option is invoked, the heading for the report still says "Media Images Report—Language Comparison").
### Media List Report
An HTML tabular report of CDR Media documents, with columns for the CDR document ID (this column can be suppressed) and the document's title. The report can optionally be filtered by media type (image, sound, or video), by language (English or Spanish), diagnoses, and/or categories. Options are available for excluding blocked documents and/or documents which have no publishable versions.
### Media Permissions Report
A tabular report of requests to use media created outside the NCI, with columns identifying the media document, the date permission was requested, the response (and its date) if applicable, the date the permission expires (if any), whether permission was also requested for use of the corresponding Spanish media (and whether that permission was granted), the use for which permission was granted, and any comments. By default, all Media documents for which permission was requested are included in the report, optionally filtered by the date of the request and/or the date of the permission's expiration, and with an option to show only requests for a single language. There is also an option to show just the requests which have been rejected, though to date such a report has always been empty. Another version of the report allows for selection of Media documents by the type of the documents for which use of the media has been requested, by the summary language and board for those using documents, or by the specific CDR ID of the summary or glossary term document for which use of media documents has been requested. Both HTML and Excel versions of the report are available.
### Published Media Documents Report
A tabular HTML report showing media documents published during a specified date range, with columns for the CDR Media documents' ID and title, date of first publication, date of the latest version, whether that version is publishable, and whether the document is blocked from use by Visuals Online. Audio media documents for glossary pronunciation or meeting recordings are excluded from the report. The report can optionally be filtered by language. Following the requirements for this report, filtering by audience behaves unusually. If only one audience is selected on the form ("Patients" or "Health Professionals") then only media documents intended for just that audience are included. Otherwise (both audiences are selected, or none are selected on the form) then only those media documents intended for both audiences are included on the report. This unusual behavior is explained clearly on the report form.
### Visual Media Caption And Content Report
An Excel report showing caption and content information for non-audio CDR Media documents. The report can be filtered by date of the last document version, diagnosis, category, language, and/or audience. The following columns are included on the report.
* CDR ID
* Title
* Diagnoses
* Proposed Summaries
* Proposed Glossary Terms
* Label Names
* Content Description
* Caption
* Image (optional)
## Term Document Reports
### Cancer Diagnosis Terms
This HTML report represents the hierarchy for the cancer diagnosis terms as nested lists, using color and indentation to indicate characteristics of the various terms. Terms at the top of the hierarchy (those which have no parent) and their direct descendants are displayed in green, while terms lower in the hierarchy are shown in blue. For the full report, aliases (alternate names) are displayed in italicized red, and are prefixed with a lowercase x. There is an option for generating a shorter version of the report, omitting the aliases.
### Cancer Intervention Or Procedure Terms
This HTML report represents the hierarchy for the cancer intervention or procedure terms as nested lists, using color and indentation to indicate characteristics of the various terms. Terms at the top of the hierarchy (those which have no parent) and their direct descendants are displayed in green, while terms lower in the hierarchy are shown in blue. For the full report, aliases (alternate names) are displayed in italicized red, and are prefixed with a lowercase x. There is an option for generating a shorter version of the report, omitting the aliases. This is a companion report for the Cancer Diagnosis Terms report.
### Clinical Trials Drug Analysis Report
This report, which can be requested as either an Excel workbook (the default) or as an HTML tabular report, shows CT.gov protocol records received during the specified date range, with columns for the NCT ID, date of receipt, and the trial's title, phase(s), alternate IDs, and sponsors. This information is needed for maintaining the CDR's drug term documents.
### Drug Review Report
An Excel workbook with three spreadsheets:
* new drugs from the NCI Thesaurus (EVS)
* new drugs in the CDR
* drugs marked as problematic and thus needing review
### EVS Concept Tools
There are several tools available for managing the CDR Term documents for drugs using concepts from the NCI Thesaurus, now generally referred to as the Enterprise Vocabulary System (EVS).
#### Refresh CDR Drug Term Documents With EVS Concepts
The first of these utilities finds CDR Term documents for drugs which are linked unambiguously to a single EVS concept, and which differ in the names and/or the definitions used by the two systems. For each such term the differences are displayed side-by-side with highlighting. Each term has a checkbox which can be used to mark the CDR Term document to be refreshed from the values in the EVS. A second checkbox is available for each term to suppress its appearance on this report. When you have finished queueing up the actions which should be performed you can click the Submit button to apply those queued actions. The form is long so you can use the Home key to return to the top of the page after queuing the desired actions. You can also submit the queued actions by pressing the Return (or Enter) key, as long as one of the radio button fields has the focus (which will be true immediately after you have clicked on any of the radio buttons). After the actions have been processed, the form will be re-drawn, with a report at the top of the page showing the details of what was done.

It takes a while (typically over a minute) when the form is first loaded. When the form is redrawn after processing the requested actions, a cache of the EVS concepts which were loaded with the initial display of the form is used, and the delay before the form is refreshed will be significantly shorter.

A separate utility is available for restoring terms which have been suppressed from this refresh interface.
#### Match CDR Terms To EVS Concepts By Name
The second tool is used for drug term concepts in the EVS which are not linked by CDR Term documents. Two tables appear for this form, with the first showing EVS drug concepts each of which matches exactly one CDR Term document by name, but that CDR document does not yet have any link to an EVS concept. Each such concept has a checkbox for queuing the generation of such a link, combined with a refresh of the values in the CDR document using the values found in the matching EVS concept. A second table appears on this form identifying EVS drug concepts for which no matching CDR Term document was found. Each of those concepts has a checkbox to queue the concept to be imported as a new CDR Term document. Below these two tables, all of the problems found during the analysis of the EVS drug concepts and the CDR drug Term documents are displayed, with sufficient details about each problem to enable a user to decide how the problem should be resolved. Submitting the queued requests works the same way as for the first utility, and you can also expect to have to wait a bit for the initial drawing of the form, which involves analysis of thousands of EVS concepts and CDR Term documents. As with the first tool, subsequent redrawing of the form is sped up by using the cache of EVS concepts created when the form was first drawn.
#### EVS Concepts Used By More Than One CDR Drug Term
The third tool is a report of EVS concepts which were found to be linked by two or more CDR Term documents. For each such concept the concept's preferred name, concept ID, and definition are displayed, followed by a list showing the CDR title and document ID for each term linked to that EVS concept. The CDR document ID links to the QC report for the CDR Term document. Use this report to examine the CDR documents and determine how to resolve the ambiguities, so that the first tool can be used for refreshing those documents.
### Non-Public Thesaurus Terms
An HTML tabular report showing CDR Term document for which the corresponding NCI Thesaurus concept has not yet been marked "Public." The following columns are contained in the report:
* CDR ID
* Concept ID
* Still Available From The Thesaurus?
* Last Modification Date
* Semantic Types
### Term Hierarchy Report
This HTML report shows how a selected CDR Term document fits in the hierarchy of the PDQ thesaurus, presenting that hierarchy as nested lists, using color and indentation to indicate the hierarchical relationships and which is the term selected for the report. The CDR ID for each of the related terms shown on the report is marked up as a link to navigate to the report for that term, and the term name for each term on the report is marked up as a link to the QC report for that term's document.
### Term Hierarchy Tree
This dynamic report presents the entire hierarchy of the PDQ thesaurus contained in the CDR Term documents, using nested HTML lists. indentation and color are used to indicate the hierarchy and which terms are leaf nodes of that hierarchy. The initial display hides all nodes except those at the top level (that is, they have no parent nodes). All non-leaf nodes can be expanded and collapsed by clicking on the `+` or `-` symbol appearing to the left of the node's term name. Each non-leaf node also has a `copy` widget which can be used to populate the system clipboard with a string containing the CDR ID of that node's term document followed by a colon and a comma-separated list of the CDR IDs of all descendants of that node.
### Term Import/Update Report
This HTML tabular report shows each event taking place during a specified date range in which a CDR Term document was newly imported or refreshed from the NCI Enterprise Vocabulary System (EVS). The report's table has columns for the CDR ID of the Term document, the Concept ID for the EVS record, the preferred name for the term, whether the event was an import of a term new to the CDR or an update of an existing term, and the date the import or update took place.
### Term Usage Report
This HTML tabular report shows all of the CDR documents using any of the terms identified in the report request. The user enters one or more Term CDR IDs on the report reequest form (the clipboard functionality of the *Term Hierarchy Tree* report is sometimes used for obtaining lists of IDs, though it is not uncommon for this report to be used for a single Term document whose CDR ID is already known to the user). The report's table has a row for each link to one of the report's Term documents, with columns for the linking document's document type, ID, and title, and the term document's ID and title. The table's caption shows the total number of links found by the report.
## Audio Processing Tools
The creation of audio pronunciation Media documents in the CDR is a multi-step process.
1. Give the contractor a spreadsheet identifying the terms needing pronunciation files.
2. Download the zip file provided by the contractor to the CDR Server.
3. Review the audio pronunciations.
4. Import new Media documents for the approved pronunciations.
### Audio Spreadsheet Creation
Generates an Excel workbook in which are recorded GlossaryTermName documents with names which need to have audio pronunciation files created. This workbook can be edited, as appropriate, to reduce the amount of work requested, or to add instructions for the contractor who created the pronunciation files. The generation of the workbook may take up to a minute or two. The Term Names sheet (the only sheet in the workbook) contains the following columns:

* **CDR** ID (unique ID for the GlossaryTermName document)
* **Term Name** (string for the name needing pronunciation)
* **Language** (English or Spanish)
* **Pronunciation** (representation of the name's pronunciation)
* **Filename** (relative path where the audio file will be stored)
* **Notes (Vanessa)** (column where contractor can enter notes)
* **Notes (NCI)** (for instructions provided to the contractor)
* **Reuse Media ID** (optional ID of Media document to be reused)

The workbook will be posted by the contractor to the NCI sFTP server as part of a zipfile, which will also contain the individual MP3 audio pronunciation files, each located in the relative path shown in the Filename column of the workbook.
### Audio Download
Files which match the pattern `Week_YYYY_WW.zip` or `Week_YYYY_WW_RevN.zip` will be retrieved from the source directory on the NCI s/FTP server and placed in the destination directory on the Windows CDR server. Then they will be copied (if running in test mode) or moved to a backup location on the s/FTP server (referred to below as the Transferred directory). By default, retrieval of a zip file will be skipped if the file already exists on the Windows CDR server (though this can be overridden). In test mode, the retrievals will be reported but not performed.
### Audio Review
Provides an interface for listening to the generated audio files in a set provided by the contractor and approving or rejecting each with an optional comment. After all of the files in a set have been reviewed, if any have been rejected, a spreadsheet containing rejected terms will be created and displayed on the user's workstation, to be saved and sent back for regeneration of the rejected pronunciations. There is also an historical report showing the pronunciations in a selected language with the specified review status (approved, rejected, or unreviewed), with columns for the term name, the review date, and the reviewer. For each pronunciation file set, a summary of the counts for each review status is also displayed, and grand totals are shown at the top of the report for all sets. It is possible to have the report only show those global status totals, omitting the details for individual sets and files. It is also possible to filter the report to only include reviews occurring during a specified date range.
### Audio Import
Creates Media documents for the MP3 files contained in the completed sets of audio pronunciation files, and creates links to those documents from the corresponding GlossaryTermName documents. Sets will be processed in the order in which they appear in the list displayed on the landing page for this tool, with MP3 clips found in later sets overriding those found in earlier sets.
## PDQ Boards
### Board Invitation History Report
HTML report showing information about when individual oncology specialists were invited to join the PDQ boards. The report can be run for one specific board or for all boards at once, optionally excluding current members or any editorial or advisory board. The set of columns to be included in the report's table can be customized to include any of the following:
* Board Name
* Area of Expertise
* Invitation Date
* Response to Invitation
* Current Member (Yes/No)
* Termination End Date
* Termination Reason
* Blank column for notes
### Board Meetings Report
Generates a table showing each of the PDQ board meetings, indicating the date/time of the meeting, and distinguishing between WebEx and in-person meetings. Two formats are available for the report, one grouping the meetings by board, and the other showing the meetings in a single chronological sequence (visually grouped by month). The user can specify which boards should be included, as well as the report's date range.
### Board Member Mailers
Form for generating word-processing letters to prospective, current, or past board members. The user selects a board, a letter template, and one or more recipients. The letters are generated as RTF documents, and links are provided for downloading the letters for mailing, possibly with optional manual editing. Examples of the types of letters available include invitations to become a member of the board (or renew an existing membership), letters welcoming new board members, or expressions of gratitude for a departing member's contribution.
### Board Roster Report
There are two scripts for generating board roster information. The first script shows information on a the current members of a specific PDQ editorial or advisory board. This report is available in two formats. The first ("Full") is an HTML page showing all information about each board member, with checkboxes for controlling whether information about subgroups, assistance, and all contact details should be included. The other format ("Summary") is a tabular report for which the user can specify which columns are to be included in the report (for example, email address, start and end dates, areas of expertise, *etc.*). The Summary version of the report is available in both Excel workbook and HTML web page versions.

The second script is similar to the first, with the following differences:
* a single report is generated for all editorial boards or all advisory boards
* fewer columns are available for the "Summary" flavor of the report
* the user can specify whether to produce a single sequence of all board members, or group the report by PDQ board
* no Excel version of the report is available from this script

There is a third script which generates a roster of the current board members as an XML document, intended for use as a service by other systems, but this service is not currently being consumed by such systems.
### Board Topics Report
An HTML report showing all the board members assigned to each of the topics for a given board. There are two versions of the report, one grouped by board member, showing all of the topics for which each board member is responsible, and the other grouped by topic, listing all of the boards members responsible for each topic. For the purpose of this report, "topic" means "summary," and the data displayed for the report is drawn from the board information stored in the `SummaryMetaData` block in each CDR Summary document.
## Summary Reports
### Changes To Summaries
This report shows text descriptions of each non-trivial change made to each summary during a specified date range. The user selects the audience for the summaries to be included in the report (patients or health professionals) and optionally a single PDQ board. The report can be restricted to summaries which can only be used as modules, summaries which can be published on their own, or all summaries, regardless of whether they can only be used as modules. The default is to report on all changes made in the previous week for all health-professional summaries for all boards. A table is provided at the top of the report showing the total number of summaries included in the report, as well as subtotals for each of the following types of summaries:
* only usable as standalone summaries
* only usable as summary modules
* usable standalone or as modules
### Get English Summary
Fetch an English CDR Summary document prepared for translation into Spanish.
### Elements Included In Summary Documents
Displays a list of CDR Summary documents, with counts of how many of the following elements are found in each document:
- Comment
- EmbeddedVideo
- MediaLink
- MiscellaneousDocLink
- StandardWording
- SummaryModuleLink
- Table

This report can help answering requests like: "Give me a summary including a video" or "I need a summary with multiple tables."
### Internal Summary Links
An Excel report showing the internal links within a specified summary. The report is used to support keeping standard treatment options in
sync during the HP reformat process. Columns are shown for the following information.
* the fragment ID of the linked target
* the section and subsection titles for the link target
* the section and subsection titles for the link source
* the text in the linking element
* whether the link source is contained in a table
* whether the link source is contained in a list
### Links To Clinical Trials From Summaries
This is an HTML tabular report of all the links to clinical trials found in Summary documents. There are two tables shown for the report. The first table gives the count of links to NLM's clinicaltrials.gov site, the count of links to NLM's cancer.gov site, and the count of linking elements for which the URL is missing. The second table has one row for each linking element found in a Summary document, with columns for the Summary document's ID, the summary title, the trial's primary protocol ID, and the linking URL (if present). There is no form for the report, as there are no user-selectable options. The report takes several minutes to generate (typically more than ten), plus a little more time to transfer the resulting report to the browser, so some patience is required.
### List Summaries
An HTML tabular report listing active (that is, excluding blocked documents) summaries in the CDR. A single table is rendered for each board's summaries. The request form for the report allows the user to control the following options for the report (all fields are required):
* which audience (Patient or Health Professional)
* which language (English or Spanish)
* whether to also include non-publishable (but unblocked) summaries
* whether to include an extra column showing the summary's CDR ID
* the number of additional blank columns to render (for notes)
* which type of summaries to include
  * only SVPC summaries
  * non-SVPC summaries which can only be used as modules
  * non-SVPC summaries which can also be published standalone
  * all non-SVPC summaries
* for non-SVPC versions of the report, the user indicates the board(s) whose summaries should be listed
### Post Translated Summary
The script used to take a Spanish summary document which has been translated in the Trados system and install it as a new Summary document in the CDR. This is the last step in a process initiated with the *Get English Summary* script described above.
### Render Sample Summary
This Python script is used to generate HTML for a sample PDQ summary provided to the PDQ data partner to demonstrate how to render the XML for a summary document as a web page.
### Summaries With Markup
An HTML tabular report showing statistics for each type of revision markup found in each summary. The user selects the board(s) to be included on the report, the audience, the language, which levels of markup to include, whether advisory board markup should be included, and whether summaries in which no revision markup is found should be included. A separate table is displayed for each board's summaries, with one row per summary and columns for the summary's CDR ID, title, and for each markup type.
### Summaries With Non-Journal Article Citations
An HTML tabular report of citations in summaries which are not citations of journal articles. The report's form requires selection of a language, and optionally allows the report to be restricted to one or more boards and/or one or more citation types. The following columns are included in the report's table:
* Summary CDR ID
* Summary Title
* Summary Section Title
* Citation Type
* Citation CDR ID
* Citation Title
* Publication Details/Other Publication Information
### Summary Changes
An HTML non-tabular report of the history of a selected summary's changes. The summary can be identified by ID or title, and the report can be for the complete history of changes to the summary, or just those changes made during a specified date range.

There is also a related report (*Summaries Type of Change*) which shows when the most recent change took place for each of the following types of change for each of the summaries selected for the report:
* new summary
* major change
* comprehensive revision
* reformat

The summaries to be included on the report can be identified by ID or title (for a report on a single summary) or by summary group (combination of board(s), audience, language, module/non-module). The form also has fields for
* which types of change to include on the report (default is all types)
* whether to include a column for comments on the changes (default is yes)
* whether to use a separate table for each type of change or a single table for the entire report (default is a single table)
* whether the report should be delivered as a web page or as an Excel workbook (default is a web page)
* whether to include all changes for a given date range, not just the most recent change for each change type (default is the most recent changes for each change type)
### Summary Citations
An HTML report listing all the citations contained in a selected summary, ordered alphabetically by the first author of the cited resource. For each citation the bibliographic identification of the resource (authors, title, journal information, etc.) is included, followed by the PubMed ID, linked to the PubMed page for the citation, opened in a separate browser tab. The summary can be selected by CDR ID or by title.
### Summary Comments
An HTML tabular report showing comments found in one or more summary documents. The form for the report allows selection of summaries by CDR ID, title, or PDQ board. For selection by board, the user must also select an audience and a language. Checkboxes are available for filtering which comments should be included in the report, as well as for adding a blank column for additional notes and/or a column showing the user who made the comment and when it was added. Each summary in the report is represented by a separate table, with a minimum of two columns: one for the title of the section in which the comment was found, and one for the text of the comment, color-coded to reflect the type of comment. The report is remarkably efficient, given the amount of work performed. The report of all comments found in all of the English health-professional summaries of the Genetics board, including the extra column showing each comment's user and date, is generated in under a single second.
### Summary Comprehensive Review Dates
A tabular report of comprehensive reviews of PDQ summary documents. The report's form has fields for filtering by summary audience, summary language, summary board(s), and summary usage (only publishable standalone or only usable as a module); for deciding whether to show all reviews or just the most recent actual review; for choosing whether to display the summaries' CDR IDs; for indicating whether to use the latest publishable versions for searching the summaries; and for determining the report format (HTML or Excel workbook). Each board has its own tables (with separate tables for standalone summaries and summary modules), with columns for CDR ID (optional), summary title, the date the review took place (if the status is "Actual") or the date the review was requested (if the status is "Planned"), review status (actual or planned), and review comment.
### Summary Last Modification Dates
An Excel tabular report of the most recent changes to the PDQ summaries. Because of the unusual requirement that all tables for the report be contained on a single worksheet, we are unable to use our standard report module, and the software for the report contains considerably more custom code than would normally be needed. Each combination of board, language, and audience is represented in a separate table on the report's worksheet. The user can specify which summaries to include on the report by board, audience, language, and module status. There are two versions of the report available.

The default version of the report shows summaries for which users have explicitly said (using the `DateLastModified` element) that non-trivial modifications were made during the date range specified for the report. This version of the report has columns for the document's ID, the summary title, the `DateLastModified` element's value, the date the summary was last saved, whether the most recent version of the summary document is publishable, and the user who saved that version.

For the alternate version of the report, the user can filter by a date range specifying when the summary documents were last saved, regardless of the `DateLastModified` values. This version of the report has all of the columns shown by the default version, as well as additional columns for the summary type (*e.g.*, "Treatment") and the summary audience (a redundant column, since each table contains only summaries for a single audience, and that audience is identified in the table's title header). In this version of the report, the date when the summary was last saved is linked to the audit report for the summary.
### Summary Mailer Report
An Excel report listing the summaries mailers sent to members of a specified PDQ board. The report's form requires selection of a single board, as well as how the report should be sorted (by board member name or by summary title) and whether the last mailer sent to each board member show be shown, or just the most recent mailer for which a response was received. The following columns are included in the report's table:
* Mailer ID
* Board Member Name
* Summary Title
* Date Mailer Sent
* Date Response Received
* Summary Changes
* Comments
### Summary Mailer Request Form
An HTML cascading form used to generate tracking records for summary mailers sent to PDQ advisory board members. The first step is to pick a PDQ board. The second step is to choose a selection method from the following options:
* Send All Summaries to all Board Members
* Select By Summary
* Select By Board Member

If the first method is chosen, the script proceeds directly to create tracking documents for each combination of the selected board's members and summaries. For either of the other two options, a picklist is presented from which the user can select on or more summaries or board members (depending on which selection method was chosen). When that form is submitted, a new form is generated with checkboxes to refine the set of mailer documents to be generated.
### Summary Metadata
An HTML tabular report showing metadata from selected PDQ summary documents. Documents can be selected by ID, title, or summary group (a combination of board, language, audience, and module status). Each summary is represented by a separate table, with label+value rows for each of the type of metadata selected from the following list:
* CDR ID
* Summary Title
* Advisory Board
* Editorial Board
* Audience
* Language
* Description
* Pretty URL
* Topics
* Purpose Text
* Summary Abstract
* Summary Keywords
* PMID

The user can also request that section metadata be included on the report, in which case a second table is shown for each summary, containing a row for each section found in the summary document, with columns for the section title (bolded for top-level sections), diagnoses covered by the section, whether the section needs a clinical trial search string, and the type(s) of the section.
### Summary Section Cleanup Report
Each `SummarySection` element in a CDR Summary document is expected to have at least one of the following child elements: `Para`, `SummarySection`, `Table`, `QandASet`, `ItemizedList`, or `OrderedList`. This is a tabular report on `SummarySection` elements which don't fulfil that requirement in CDR Summary documents. The documents to be included in the report can be selected by summary group (board/audience/language combination), CDR ID, or summary title. The user can request either an HTML report or an Excel workbook. Each summary on the report is represented by its own row, with columns for the document ID, the document title, and the anomalous `SummarySection` elements found in the document.
### Summary Standard Wording Report
A tabular report which identifies the presence of one or more words or phrases in CDR Summary documents, and for each occurrence reports whether that occurrence is marked up with the `StandardWording` element. The user can select summaries by ID, title, or summary group (that is, board/audience/language combinations). One or more search terms are specified on the report request form, and the software uses the CDR glossary term information to expand the search to also find variant names for the terms. There is also a checkbox for including blocked documents, which are excluded from the report by default. The report can be requested as an HTML page or as an Excel workbook. The report's table has columns for the summary document's ID, the summary title, the exact form of the matched phrase, the context in which the phrase was found (the section title and the surrounding text in which the phrase was found, with the phrase highlighted by distinctive typography), and whether the phrase was marked up as `StandardWording`. The table's caption identifies all forms of the terms sought for the report.
### Summary Table Of Contents Report
Shows the hierarchical tables of contents for one or more Cancer Information Summaries. Formatting (color, strikeout) is used to render revision markup (insertions and deletions). The user can select summaries to be included for the report by CDR ID, summary title, or PDQ board(s). When selecting by PDQ board, additional filtering by audience and language is required. The depth to recurse for the level of section nesting defaults to 3, but can be overridden by the user.
### SVPC Summaries Report
Early in the 2020s a project was launched to create patient-oriented Summary documents which consolidated related information which our users were looking for from separate web pages into a single page. The project has been known by the names *Single View of Patient Content* (SVPC) and *Consumer-Focused Content Modernization* (CFCM). In some cases the resulting content is contained in completely new summary documents, and in other cases existing summaries were converted to reflect the new approach. This report lists all of these summaries either published during a specified date range or not yet published. In addition to the date-range fields, the report form has options for
* narrowing the report by summary language (English or Spanish)
* including non-publishable summaries
* including the description of the summary
* including the summary URL
* displaying whether the summary is publishable
* including linked partner summaries
* specifying whether the report should be delivered as an HTML web page or as an Excel workbook

In addition to the optional columns described above, the table for the report includes columns for the summary document's CDR ID, the summary title, the summary type, and the latest publication date (if any)
### Updated SummaryRef Titles
This report shows summary documents in which the denormalized titles in SummaryRef elements have been updated by a global change job to reflect modifications in the titles of the linked summaries. Each row in the report has three columns, showing the CDR ID of the linking and linked summary documents, as well as the date and time when each linking document was modified.

The global change job is performed by a CGI web admin script, but that script does not appear in the CDR admin menus. It is instead invoked by a macro installed in XMetaL, where the command appears on the popup context menu drawn for Summary documents.
## System Tools
### Health Monitoring Scripts
There are two scripts for checking whether the CDR server for a given tier is up. The first (`/cgi-bin/cdr/ping.py`) confirms that the web server is actively processing requests and that Python scripting is configured correctly. The second (`/cgi-bin/cdr/cdr-ping.py`) also confirms that the CDR API is installed and working. This second script is invoked by the CBIIT system monitoring software to periodically confirm that the CDR server is available by testing to verify that the text content of the server's response is "OK."
### CDR Admin Menu Hierarchy
The `/cgi-bin/cdr/CdrMenus.py` script generates an HTML report which recursively shows the menus for the CDR Admin web pages. This report is used when the users are asked to review the available reports and tools to identify which are no longer in use and can be retired, as well as when systemic changes have been made to the software, and comprehensive testing of all of the reports and tools is needed. There are a little under 500 menu items in the hierarchy, representing a little over 200 unique scripts.
### Check Authorization
Web service to report whether the account for a given CDR login session is allowed to perform a specified action. Not currently used.
### Tier Settings Check
Report on the health of the CDR host name settings and database credentials.
### Check Dev Data
Reports on differences between what the CDR development tier looks like following a database refresh from the production tier compared with the snapshot of the development tier taken immediately prior to that refresh. This allows us to make sure we have preserve software differences which should still be present on the development tier, even as we update the CDR documents which should reflect those on the production tier.
### Check Manifest
Examines the manifest file for the CDR client files and reports any discrepancies found with the actual files in the `ClientFiles` directory.
### Database Tables
An HTML report displaying the definitions for all of the database tables in the CDR.
### Edit Actions
The CDR controls which accounts are allowed to perform which actions by assigning accounts to groups, each of which groups is granted permission to perform a specified set of actions. Some of the actions support making that permission assignment on a per-document-type basis, and others are independent of any document types. This interface supports the management of the available CDR actions.
### Edit Document Types
Interface for adding new document types or editing existing types, specifying the type's name, schema document, title filter, optional comments, and whether the type is still active. The form for an existing document type included a display of all of the valid value lists extracted from the type's schema.
### Edit External Maps
The CDR supports association of string values from various external sources with specific CDR documents. When the CDR was used to track clinical trials this feature was used extensively. Now that clinical trial tracking has been split off to another division of the NCI this feature is only used for associating dictionary term aliases with the corresponding glossary term documents. A web interface is provided for viewing and editing these external values, with the ability to filter based on various criteria, edit the mappings, and record which values are mappable.
### Edit Groups
This interface supports adding, removing, and editing CDR groups. The editing interface for a specific group has fields for:
* the group's name
* an optional description of the group's uses
* which user accounts are members of the group
* which document-type-independent actions are allowed for the group
* which document types are allowed for actions (such as adding or publishing documents) for which permissions are assigned by document type.

There is also an HTML tabular report showing which users are members of which groups. This is an unwieldy report, as it contains rows for each group and columns for each user, making it very wide, but it nevertheless provides a useful overview for CDR group membership.
### Edit Link Control Tables
Links between CDR documents are validated using tables which specify which elements in which document types are allowed to link to which target document types. These allowed combinations are stored as named link types, with each link type specifying one or more element/doctype combination, one or more link target doctypes, whether the target document must have a version, and if so, whether that version must be publishable. Custom rules can be associated with a link type to control more precisely the conditions under which linking is allowed for this type. A web interface is provided for creating, deleting, and editing these link types. The interface also provides a tabular HTML report listing each allowable source/target combination for links in the CDR.
### Edit Query Term Definitions
In order to support document searching in the CDR, the text content of selected document elements and attributes are indexed in a pair of tables, one for the current working copy of all documents, and a second for the latest publishable versions of documents. A third table stores the paths for which such indexing should be performed (either with absolute paths or `xpath` using the `//` prefix indicating an element or attribute appearing anywhere in any document). An interface is provided for adding or removing paths from this control table. The interface also provides a report comparing the set of indexable paths between two CDR tiers.
### Edit Server Configuration
Each CDR server has several files in the `/etc` directory which control which values are used by the server on a given tier (for example, host names, database ports, *etc.*). This interface allows one of the CDR developers to edit those files.
### Edit User Accounts
An interface is provided for creating, editing, and retiring CDR user accounts, with fields for account name, user's full name, contact information, an optional comment describing the type of work performed by the user, and group membership. Two types of account are available. The most commonly used type allows login from outside the CDR server, using the NIH authentication system. For this account type, no login credentials are stored in the CDR database (beyond the CDR account name, which matches the NIH account name). The second type, used for machine accounts, only allows login locally on the CDR server itself for batch and scheduled processing, and a password is required for these accounts. The hash for the password is stored in the database and is used to authenticate login requests.
### Edit Value Table
Interface for managing value value control tables. The script implements three separate form pages:
1. a form for selecting a table
2. a form for selecting a value
3. a form for adding/editing/dropping a value

This class/script can be used to support any table of valid values comprised as having exactly these columns:
* **value_id** - primary key (integer) automatically generated by the DBMS
* **value_name** - required display name for the value (VARCHAR(128)
* **value_pos** - required unique integer controlling position of value on pick lists

There are currently four tables (all used in support of the CDR document translation queues) editable by this interface:
* `glossary_translation_state`
* `media_translation_state`
* `summary_translation_state`
* `summary_change_type`
### Fail Batch Job
This tool marks stalled publishing and batch jobs (usually caused by a server crash) as failed so that attempts to create new jobs are not blocked. The landing page for the tool lists the stalled and active jobs, and the user selects the job(s) which need to be resolved and press the **Submit** button.
### Fetch CDR Settings
Service providing a JSON report showing the settings for the CDR server on a specific tier. Used by a command-line script in the developer utilities for comparing the CDR servers on two or more tiers to confirm that CBIIT has configured them the same way. Only accessible by authenticated admin users.
### Filter Documents
A static web page (`CdrFilter.html`) provides a form for testing running CDR filters and filter sets. The form is backed by a Python script which executes the filter(s) against the selected document. There are many settable options controlling canned as well as custom parameters. There are also buttons for validating the filtered results and for showing the QC filter sets containing the selected filters.
### Fix Permissions
Sometimes the Windows file system scrambles its permission settings for some of the files/directories. This script allows a developer to correct such problems.
### Get Filter
RESTful API for fetching a CDR Filter document's XML. Used for comparing filters across tiers.
### Get PDQ Contacts
Service to fetch the active PDQ data partner contacts as XML. Used by the scheduled job to notify partners of new PDQ data availability.
### Get PDQ Partners
Service to fetch the PDQ data partners as XML. Used by the report on SFTP retrieval activity for the PDQ data.
### Install DTD
Install an updated version of one of the two DTD files used for publishing, repesenting the documents as published to the NCI web site, or the documents as published for the data partners.
### Install Schema
Script for installing a new or modified schema on the CDR server for a given tier. The schema is also parsed, producing a DTD file which is installed in the client files set, following which a fresh client files manifest is generated.
### Manage Client Files
There is a web interface for installing a new client file (or an updated version of an existing client file) on the current tier. After the file is installed the client file manifest is regenerated and a report showing the output of that process is displayed. There is a comparable interface for fetching a client file from the server, as well as an interface for removing a client file selected from a dropdown list.
### Manage Control Values
The CDR has a generic table of control values used to control runtime behavior. The values are each assigned to a named group, and are given a unique name within that group. For example, the ElasticSearch schemas for the dictionary loaders are stored in the "dictionary" group. This interface supports the creation, editing, and deletion of these control values for the current tier.
### Manage Filters
A web interface is provided for managing the set of XSL/T filters used in the CDR, with the following capabilities:
* view the list of all filters, sorted by filter title or by CDR ID
* view the source code for a specific filter
* report the differences between the filters on a lower-tier CDR server with those on the production server
* perform a comparison between two tiers for a specific filter
* generate a report showing all parameters used in CDR filters, with identification of each filter in which each paramater is used
### Manage Filter Sets
Named sets of CDR filters can be created and run against a document in sequence. A web interface is provided for creating, editing, and deleting these filter sets. The editing interface supports drag-and-drop manipulation to control the sets membership and the order of those members. Membership can be nested, that is, a filter set can contain another filter set as a member alongside members which are individual filters. In addition to the membership and the set's name, each filter set can be given a brief description string as well as notes explaining how the set is intended to be used. The interface also provides two reports: a shallow report which shows each set with its direct members, and a deep report which recurses into nested sets, showing all filters which will be applied to a document in the order of processing, and identifying the nested sets in which recursively included filters are contained.
### Manage Glossary Servers
Manage the list of servers to which we push fresh glossary information. The list of servers is used by the CDR scheduler when it assembles data for finding glossary terms which can be marked up with links to glossary popups. That data is serialized and sent to each of the servers on the list managed by this script.
### Manage Publishing Job Status
This page is for managing the status of unfinished publishing jobs, either by marking an unfinished (possibly stalled) job as failed, or (in the case of a job which is waiting for approval before proceeding), releasing the held job. Note that if ALL documents for a job need to be pushed, it is necessary to fail the job, and manually submit a push job with the PushAllDocs paramater set to Yes.
### Manage Scheduled Jobs
The landing page for this tool displays a table of the scheduled jobs for this tier, with columns showing the job name, the class implementing the job, whether the job is enabled, and what schedule is used for running the job. The column for the job name links to the form for editing the job's settings, with fields for the job name, its implementing class, the schedule, options for the job (as name/value pairs), and whether the job is enabled. There are buttons attached to the form for saving the changes, deleting the job, manually running the job, and returning to the table for all jobs.
### Manage Translation Job Queues
There are multiple translation job queues for the CDR, each tracking active translation jobs and their statuses for one or more related document types. Tools are available for managing the status of each job, as well as for performing bulk operations on the individual queues. There are translation queues for glossary document, media documents and summary documents. For the summary translation jobs users can attach files which should be included with email notification of updates in the status of a job. There are reports for each of the translation queues (active and historical).
### Message Logged-In Users
An HTML form for sending an email message to currently logged-in users, typically to alert them of an unscheduled disruption to system availability.
### Open Sessions
An HTML tabular report showing the currently open (not logged off or expired) sessions on the tier of the server from which the report is requested. The report contains columns for the following information:
* the primary key (id) for the session
* the date and time the session was started
* the date and time an action was performed for the session
* the session's account name
* the full user name for the account
* the email address for the account's user (if available)
* the phone number for the account's user (if available)
### Recent CDR Logons
Tabular HTML report of recent CDR logon sessions. This is a utility used to track down events when users get confused about what they've been doing in the CDR. Contains columns for the user account name, full name, session ID, date/time of logon (and logoff when appropriate). Not included in the CDR Admin menus, as this is only used by developers, and not very often.
### Refresh Client Files
Web service invoked by the CDR XMetaL loader script prior to launching XMetaL, in order to ensure that the user's machine has the current CDR client files for the selected tier. The service must be invoked with a POST request.
### Replace CWD With Older Version
This program will replace the current working version of a document with the XML text of an earlier version. It can be used to restore the status of a document after it was damaged in some way. The Doc ID and Version fields are both required. An optional Comment field is included, as well as checkboxes for optionally also creating a new version, and for making that version publishable.

A warning is displayed on the form reminding the user that replacing the CWD with an older version will obscure and complicate the true version history and will override recent changes. Therefore this tool should be used very sparingly, only when there is a serious problem with the CWD that cannot be recovered by a simple edit.

There is also a tabular HTML report showing the replacements performed with this tool, optional with filters for earliest date, user ID, document type, and/or CDR ID. The table has columns for the date/time of the replacement, the document ID, the document type, the user name, the number of the most recent version at the time of replacement, the number of the most recent publishable version at the time of replacement, whether the CWD was changed from the most recent version before the replacement was made, the number of the version selected for the replacement, whether a new version was also created, whether that version was made publishable, and any comment entered for the replacement.
### Replace Old Document With New Document
This program replaces the XML of a CDR document with the XML copied from another CDR document. This is typically done in the case of a summary which is undergoing significant modifications which requires work over a longer period of time. In order to be able to make minor corrections to the original documentation during this period, the new version of the summary is prepared as a separate, temporary document. When the work on the new version is complete and has been approved for replacement of the original summary, the XML from the new temporary document is copied as a new unpublishable version of the original summary, and the temporary document is marked as blocked to prevent it from being inadvertently published. In these instructions, the original document, whose contents will be updated, is referred to as the 'old' document, and the temporary document whose XML will be copied into the permanent ('old') summary, is referred to as the 'new' document.

All of the following conditions must be met before replacment will proceed:
* The user must be authorized to perform this operation.
* The old and new documents must both be Summaries.
* The new replacement document must have a `WillReplace` element with a `cdr:ref` attribute referencing the old document.
* After receiving feedback, the user must confirm that the replacement should proceed.

The user first enters the CDR document ID for the old (replaced) and new (replacement) documents on the form and clicks the Submit button. The program then checks to see if the first three conditions above are met. If they are, the program will report to the user:

* The titles of the respective old and new documents.
* The validation status of the new document.
* A list of any documents that have links to specific fragments in the old document. Any such links will need to be resolved after the new document replaces the old. The user must then confirm that this replacement should proceed. If replacement is confirmed, the program will do the following:
* Check out both documents. If either document is locked by someone else, the program will stop.
* Version the current working document for the old document, if it is different from the last saved version.
* Remove the WillReplace element from the new document.
* Save the current working document for the new document as a non-publishable version under the old ID.
* Mark the now unused ID of the new document as blocked. That ID will no longer be used in the CDR.
### Clear Filesweeper Lockfile
Web utility for removing a lockfile left behind by an aborted run of the scheduled job which archives and/or removes older files which no longer need to be kept directly in the file system of the CDR server. The lockfile prevents two simultaneous processes from running this script at the same time. Removing the lockfile after an aborted run is necessary in order for subsequent scheduled runs to proceed.
### Report On Available Disk Space
An HTML report showing the total disk space, the amount of space in use, and the amount of space remaining for the C: and D: drives of the CDR server for the tier on which the report is invoked. A scheduled job checks this report for all tiers periodically and sends an email alert to the development team if disk space drops below a safe threshold.
### Show Client Logs
Displays client logs, used to track down what might be causing XMetaL to lock up or crash. Filterable by user and/or date range. Available for activity in the spring of 2023 (when the CDR switched to Python scripting for XMetaL) and later. There is an older script (`ShowClientEvents.py`) which displays client events from earlier, when a custom DLL (compiled from C++) was used to support scripting in JavaScript.
### Show Server Logs
A report showing the most recent lines of a selected server log file, selected from a picklist containing all of the log files in the `cdr/Log` directory on the CDR server.
### SQL Server Blocking Requests
Tabular HTML report used for troubleshooting blocking database requests (not on the menus). Table contains the following columns:
* Server Process ID
* Blocked By
* Wait Time
* Last Wait Type
* Wait Resource
* CPU Usage
* Physical I/O
* Memory Usage
* Database
* User ID
* Login Name
* NT User Name
* NT Domain
* Host Name
* Program Name
* Host Process
* Current Command
* Net Address
* Net Library
* Login Time
* Last Request
* Subthread ID
* Open Transaction Count
* Status
### Test Python Upgrade
This HTML report does not appear on the CDR administrative menus, but it can be run at any time, and is always run following an upgrade of the CDR server's Python interpreter. The report contains two tables. The first table shows the status of each of the critical non-core modules imported by the CDR software, with columns for the module name, a description of the module and how it is used by the CDR, and the module's status (a green "OK" is what we want to see for each row). The second table lists all of the third-party Python modules installed on the server, with columns for the installation package name, the module import name, and the version number.
### Unlock Documents
This utility allows a user with sufficient permission to release the locks for one or more CDR documents which have been left checked out. The form has fields for the CDR IDs of the documents to be unlocked, the tier on which to unlock the selected documents, the session ID of the user requesting the unlock (required because of the support for cross-tier requests), and an optional reason to be recorded explaining why the documents are being checked back in.
### Unlock Media
The directory in which CDR media documents are staged for syncing with Akamai's content delivery network (CDN) is locked in preparation for that staging by renaming it from "media" to "media.locked" and then unlocked after the staging by reversing that name change. If the publishing software is interrupted during that staging process for any reason (for example, an unscheduled server reboot, or a network failure), the directory will be left in the locked state, preventing subsequent jobs from being able to process media documents. This utility allows a developer to unlock the directory. There are fields on the form for overriding the default strings for the locked and unlocked path names.
