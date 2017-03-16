#----------------------------------------------------------------------
# Globally change all links (cdr:ref or href) of any specified type from
# one value to one or more others.
#
# Works on any simple link: cdr:ref and cdr:href, with or without
# #fragment ids appended to the linking doc ID.
#
# This replaces GlobalChangeSimpleLink.py adding the following new
# functionality:
#   Can retain old link and just supplement it with a new one.
#   Can add more than one new link.
#
# BZIssue::4955
#
#                                           Alan Meyer, December 2010
#----------------------------------------------------------------------
import cdrcgi, cdr, cdrbatch, GlobalChangeLinkBatch

#----------------------------------------------------------------------
# Main
#----------------------------------------------------------------------
if __name__ == "__main__":
    # Parse form variables and make everything accessible
    linkVars = GlobalChangeLinkBatch.SimpleLinkVars()

    # Check authorization
    if not cdr.canDo(linkVars.session, "GLOBAL LINK CHANGE"):
        cdrcgi.bail("Sorry, you are not authorized to make global link changes")

    # Process cancel request, if any
    if linkVars.request in ('Cancel', 'Admin System'):
        cdrcgi.navigateTo("Admin.py", linkVars.session)

    # Process all of the parts we need, in order
    linkVars.chkSrcDocType()
    linkVars.chkSrcElement()
    linkVars.chkLinkRef("old", 0)

    # Multiple new links are allowed
    # First one is always checked, others may be
    linkVars.chkLinkRef("new", 0)
    i = 1
    while i < GlobalChangeLinkBatch.MAX_ADD_LINKS:

        # DEBUG
        # cdr.logwrite(
        # "GlobalChangeLink cgi: i=%d  idStr=%s  refName=%s  addMore=%s" %
        #             (i, linkVars.getVar("newLinkRefIdStr%d" % i),
        #                 linkVars.getVar("newLinkRefName%d" % i),
        #                 linkVars.getVar("addMore")))

        # If we have data for one of these check it
        # Or if we are asked to do more, do it

        if (linkVars.getVar("newLinkRefIdStr%d" % i) is not None or
            linkVars.getVar("newLinkRefName%d" % i) is not None or
            linkVars.getVar("addMore") == 'Yes'):
                linkVars.chkLinkRef("new", i)
        else:
            break
        i += 1

    # Back to simple variables
    linkVars.chkRefTypes()
    linkVars.chkEmailList()
    linkVars.chkRunMode()
    linkVars.showWhatWillChange()

    # If we got here with no cancellation, create the batch job using
    #   data stored in the linkVars object
    cmd=cdr.BASEDIR + "/lib/Python/GlobalChangeLinkBatch.py"
    batchJob = cdrbatch.CdrBatch(
                jobName=GlobalChangeLinkBatch.JOB_NAME,
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
