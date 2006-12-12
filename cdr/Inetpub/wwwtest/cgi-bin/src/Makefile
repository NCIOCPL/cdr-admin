#----------------------------------------------------------------------
#
# $Id: Makefile,v 1.1 2006-12-12 15:41:46 bkline Exp $
#
# Rules for building libraries for CGI.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

CSC=csc
CSFLAGS=/target:library
CDR_CLIENT=CdrClient

all: $(CDR_CLIENT).dll
	@echo Assemblies up to date

$(CDR_CLIENT).dll: $(CDR_CLIENT).cs
	$(CSC) $(CSFLAGS) /out:../bin/$(CDR_CLIENT).dll
