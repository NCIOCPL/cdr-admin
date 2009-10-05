#--------------------------------------------------------------------------
#
# $Id: makefile,v 1.1 2002-01-30 18:32:55 mruben Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/01/30 18:24:58  mruben
# Added makefile to install
#
# Revision 1.1  2002/01/30 00:02:38  mruben
# added makefile for installation
#
#
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
# Makefile variables
#--------------------------------------------------------------------------

CDRWEB		= $(DRV)/Inetpub/wwwtest
CVSUPD		= cvs update

CP		= cp -f

WEB_PAGES	= CdrFilter.html EditCdrFilter.html 


# phony all to prevent accidental installation by simply typing make
all:

cvsupdate:
	$(CVSUPD)

install:	cvsupdate
	$(MAKE) _install

_install:
	$(CP) $(WEB_PAGES) $(CDRWEB)

