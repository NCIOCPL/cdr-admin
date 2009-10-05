#----------------------------------------------------------------------
# $Id: GlobalChangeSimpleLink.py,v 1.2 2009-07-23 23:45:50 ameyer Exp $
#
# Globally change all links (cdr:ref) of any specified type from
# one value to another.
#
# Works on any simple link: cdr:ref and cdr:href, with or without
# #fragment ids appended to the linking doc ID.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/07/22 01:24:20  ameyer
# Initial version.
#
#
#----------------------------------------------------------------------
import cdrcgi, cdr, cdrbatch, SimpleLinkGlobalChangeBatch

#----------------------------------------------------------------------
# Main
#----------------------------------------------------------------------
if __name__ == "__main__":
    # Parse form variables and make everything accessible
    linkVars = SimpleLinkGlobalChangeBatch.SimpleLinkVars()

    # Check authorization
    if not cdr.canDo(linkVars.session, "GLOBAL LINK CHANGE"):
        cdrcgi.bail("Sorry, you are not authorized to make global link changes")

    # Process cancel request, if any
    if linkVars.request in ('Cancel', 'Admin System'):
        cdrcgi.navigateTo("Admin.py", linkVars.session)

    # Process all of the parts we need, in order
    linkVars.chkSrcDocType()
    linkVars.chkSrcElement()
    linkVars.chkLinkRef("old")
    linkVars.chkLinkRef("new")
    linkVars.chkRefTypes()
    linkVars.chkEmailList()
    linkVars.chkRunMode()
    linkVars.showWhatWillChange()

    # If we got here with no cancellation, create the batch job using
    #   data stored in the linkVars object
    cmd=cdr.BASEDIR + "/lib/Python/SimpleLinkGlobalChangeBatch.py"
    batchJob = cdrbatch.CdrBatch(
                jobName=SimpleLinkGlobalChangeBatch.JOB_NAME,
                command=cmd, args=linkVars.linkVarsToBatchArgs())

    # Queue it up for starting
    try:
        batchJob.queue()
    except Exception, info:
        cdrcgi.bail("Unable to start batch job: %s" % str(info))

    # Report to user
    html = u"""
<h4>The global change has been queued for batch processing</h4>
<p>To monitor the status of the job, click this
<a href='getBatchStatus.py?Session=%s&jobId=%s'><u>link</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
""" % (linkVars.session, batchJob.getJobId())

    linkVars.sendPage(html, subBanner="Global change initiated",
                      buttons=("Admin System",))
