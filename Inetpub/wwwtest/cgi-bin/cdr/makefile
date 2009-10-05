#--------------------------------------------------------------------------
#
# $Id: makefile,v 1.1 2002-01-30 18:24:58 mruben Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/01/30 00:02:38  mruben
# added makefile for installation
#
#
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
# Makefile variables
#--------------------------------------------------------------------------

CDRWEBCGI	= $(DRV)/Inetpub/wwwtest/cgi-bin/cdr
CVSUPD		= cvs update

CP		= cp -f

PYTHON_PROGRAMS	= Admin.py AdvancedSearch.py cdrcgi.py CdrReport.py \
                  CheckUrls.py CitationSearch.py CiteSearch.py \
		  ConceptTermReviewReport.py DevTasks.py DumpParams.py \
		  EditAction.py EditActions.py EditCSS.py EditCSSs.py \
		  EditDocType.py EditDocTypes.py EditFilter.py \
		  EditGroup.py EditGroups.py EditIssue.py \
		  EditLinkControl.py EditLinkType.py EditQueryTermDefs.py \
		  EditUser.py EditUsers.py Filter.py GeoSearch.py \
		  GetTree.py Glossary.py LinkedDocs.py ListIssues.py \
		  Logout.py Mailers.py MergeProt.py MiscSearch.py \
		  ModifiedPubMedDocs.py NewPhysicianInitMailerReqForm.py \
		  OrgSearch.py OrgSearch2.py PdqBoards.py \
		  PDQMailerRequestForm.py PersonLocSearch.py \
		  PersonOrgLocLinks.py PersonSearch.py pptest.py \
		  ProtAbstractMailerReqForm.py \
		  ProtAbstractUpdateMailer.py ProtSearch.py publishing.py \
		  PublishPreview.py PubStatus.py Reports.py \
		  SearchForm.py ShowAllLinkTypes.py ShowDocXml.py \
		  StatAndParticMailer.py StatAndParticUpdateMailer.py \
		  SummarySearch.py TermHierarchy.py TermLinks.py \
		  TermsByType.py TermSearch.py TermSrch.py TermTree.py \
		  TermTree2.py TermTree3.py TermTreeB.py TermTreeB2.py \
		  TermTreeS.py TermUsage.py UnchangedDocs.py

PERL_PROGRAMS	= DumpParams.pl 


# phony all to prevent accidental installation by simply typing make
all:

cvsupdate:
	$(CVSUPD)

install:	cvsupdate
	$(MAKE) _install

_install:
	$(CP) $(PYTHON_PROGRAMS) $(CDRWEBCGI)
	$(CP) $(PERL_PROGRAMS) $(CDRWEBCGI)

