/**
 * Jobs collection
 *
 * @author wenbin@nextdoor.com
 *
 */

require.config({
  paths: {
    'jquery': 'vendor/jquery',
    'underscore': 'vendor/underscore',
    'backbone': 'vendor/backbone',

    'utils': 'utils',
    'config': 'config',
    'jobModel': 'models/job'
  },
  waitSeconds: 10,

  shim: {
    'backbone': {
      deps: ['underscore', 'jquery'],
      exports: 'Backbone'
    }
  }
});

define(['utils',
        'jobModel',
        'config',
        'backbone',
        'vendor/URIjs/URI'], function(utils, JobModel, config, backbone, URI) {
  var jobsCollection = undefined;

  return Backbone.Collection.extend({
    initialize: function(options) {
      jobsCollection = this;
    },

    
    //A nice place to define our parameter,.
	CDR_SESSION_PARAM: "Session",

    /*------------------------------------------------------------------------------
     * Completely ugly hack to make sure web service calls have a Session ID.
     * This *should* be done via the cdr_auth module, except that (A) that's not
     * module and (B) even after converting it to a module, nothing seems to work
     * for making it avaialble.
     *-----------------------------------------------------------------------------*/
    _doSessionIDHack : function(modelUrl) {
        var modifiedUrl;
         
        if(modelUrl != null && modelUrl.trim() != "") {

            var myModelURL = URI(modelUrl);

			// If the Model URL doesn't a Session parameter, add one if it exists.
			if (!myModelURL.hasQuery(this.CDR_SESSION_PARAM)) {

				//Get the current session ID
				var sessionID = this._getSessionID();

				if (sessionID != "") {
					myModelURL.addQuery(this.CDR_SESSION_PARAM, sessionID);
				} else {
					//No Session, then there is a problem
					window.console && console.log('Session parameter, ' + this.CDR_SESSION_PARAM + ', is missing.');
				}

				modifiedUrl = myModelURL.toString();
            }

        } else {
			// Something is wrong. There should really be a URL. The calling function
            // will probably fail.
             window.console("No model URL was passed in.")
             modifiedUrl = modelUrl;
         }
         
         return modifiedUrl;
    },
    
    _getSessionID : function() {
        var pageURI = URI(window.location.href);
        
        var sessionID = "";
        
        if(pageURI.hasQuery(this.CDR_SESSION_PARAM)) {
            sessionID = pageURI.search(true)[this.CDR_SESSION_PARAM];
        }
        
        return sessionID;
    },
    
    /*-----------------------------------------------------------------------------*
     *  END OF UGLY HACK
     *-----------------------------------------------------------------------------*/
    
    
    /**
     * Returns total number of jobs.
     *
     * @return {number} total number of jobs.
     */
    getTotal: function() {
      return this.jobs.length;
    },

    /**
     * Returns total number of active jobs.
     *
     * @return {number} total number of active jobs.
     */
    getActiveCount: function() {
      return _.filter(this.jobs, function(job) {
        return job.get('next_run_time') !== '';
      }).length;
    },

    /**
     * Returns total number of inactive jobs.
     *
     * @return {number} total number of inactive jobs.
     */
    getInactiveCount: function() {
      return this.getTotal() - this.getActiveCount();
    },

    /**
     * Fetches jobs.
     */
    getJobs: function() {
      this.url = config.jobs_url;
      this.fetch();
    },

    /**
     * Fetch a job.
     *
     * @param {string} jobId string for job id.
     */
    getJob: function(jobId) {
      this.url = config.jobs_url + '/' + jobId;
      this.fetch();
    },

    /**
     * Parses response from scheduler api server.
     *
     * @param {object} response the response returned from api server.
     * @return {Array} an array of objects of JobModel.
     */
    parse: function(response) {
      var jobs = response.jobs;

      // If api server returns a single job, then make an array here.
      if (!jobs) {
        jobs = [response];
      }

      this.jobs = [];
      _.each(jobs, function(job) {
        this.jobs.push(new JobModel(job));
      }, this);
      return this.jobs;
    },

    /**
     * Run a job.
     *
     * @param {string} jobId
     */
    runJob: function(jobId) {
      $.ajax({
        url: this._doSessionIDHack(config.executions_url + '/' + jobId),
        type: 'POST',
        success: this._runJobSuccess,
        error: this._runJobError
      });
    },

    _runJobSuccess: function() {
      utils.alertSuccess('Success! Job is scheduled to run.');
    },

    _runJobError: function() {
      utils.alertError('Failed to schedule the job.');
    },

    /**
     * Add a job.
     */
    addJob: function(data) {
      $.ajax({
        url: this._doSessionIDHack(config.jobs_url),
        type: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json; charset=utf-8',
        success: this._addJobSuccess,
        error: this._addJobError
      });
    },

    _addJobSuccess: function() {
      utils.alertSuccess('Success! Job is added.');
      jobsCollection.trigger('reset');
    },

    _addJobError: function(err) {
      utils.alertError('Failed to add the job.\n' + err.statusText);
    },

    /**
     * Delete a job.
     *
     * @param {String} jobId The id of job to be deleted.
     */
    deleteJob: function(jobId) {
      $.ajax({
        url: this._doSessionIDHack(config.jobs_url + '/' + jobId),
        type: 'DELETE',
        success: this._deleteJobSuccess,
        error: this._deleteJobError
      });
    },

    _deleteJobSuccess: function() {
      utils.alertSuccess('Success! Job is deleted.');
      jobsCollection.trigger('reset');
    },

    _deleteJobError: function() {
      utils.alertError('Failed to delete the job.');
    },

    /**
     * Modify a job.
     *
     * @param {string} jobId
     * @param {object} data json object for new job data.
     */
    modifyJob: function(jobId, data) {
      $.ajax({
        url: this._doSessionIDHack(config.jobs_url + '/' + jobId),
        type: 'PUT',
        data: JSON.stringify(data),
        contentType: 'application/json; charset=utf-8',
        success: this._editJobSuccess,
        error: this._editJobError
      });
    },

    _editJobSuccess: function() {
      utils.alertSuccess('Success! Job is modified.');
      jobsCollection.trigger('reset');
    },

    _editJobError: function(err) {
      utils.alertError('Failed to modify the job.\n' + err.statusText);
    },

    /**
     * Pause a job.
     *
     * @param {string} jobId
     */
    pauseJob: function(jobId) {
        $.ajax({
        url: this._doSessionIDHack(config.jobs_url + '/' + jobId),
        type: 'PATCH',
        success: this._pauseJobSuccess,
        error: this._pauseJobError
      });
    },

    _pauseJobSuccess: function() {
      utils.alertSuccess('Success! Job becomes inactive.');
      jobsCollection.trigger('reset');
    },

    _pauseJobError: function() {
      utils.alertError('Failed to pause the job.');
    },

    /**
     * Resume a job.
     * @param {string} jobId
     */
    resumeJob: function(jobId) {
      $.ajax({
        url: this._doSessionIDHack(config.jobs_url + '/' + jobId),
        type: 'OPTIONS',
        success: this._resumeJobSuccess,
        error: this._resumeJobError
      });
    },

    _resumeJobSuccess: function() {
      utils.alertSuccess('Success! Job becomes active.');
      jobsCollection.trigger('reset');
    },

    _resumeJobError: function() {
      utils.alertError('Failed to resume the job.');
    }
  });
});
