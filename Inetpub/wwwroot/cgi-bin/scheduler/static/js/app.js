require.config({
  urlArgs: 'bust=' + cacheBuster,
  baseUrl: 'static/js',
  paths: {
    'jquery': 'vendor/jquery',
    'backbone': 'vendor/backbone',
    'underscore': 'vendor/underscore',

    'jobs-view': 'views/jobs/jobs-view',
    'executions-view': 'views/executions/executions-view',
    'logs-view': 'views/logs/logs-view',

    'jobs-collection': 'models/jobs',
    'executions-collection': 'models/executions',
    'logs-collection': 'models/logs'
  },
  waitSeconds: 10,

  shim: {
    'backbone': {
      deps: ['underscore', 'jquery'],
      exports: 'Backbone'
    }
  }
});

// We used to have a single require(...) call with one list of dependencies
// and a single callback containing the main code for the application.
// In that approach, the first ajax callback after page loading would
// intermittently fail (about 2.3% of the time, or once every 43 attempts)
// because the callback for the require() call in hacks/cdr_auth.js had
// not yet been invoked before the code for the single require()'s callback
// function was run. This meant that the Backbone.sync() method had not yet
// been overridden, so the CDR session ID was not being added to the query
// portion of the ajax URL. With the nesting used here, we have never seen
// such a failure. Another possible solution would have been to use define(...)
// instead of require(...) in hacks/cdr_auth.js (with a return of some
// arbitrary object). We haven't been able to find any documentation
// supporting this theory, but we are guessing that using define(...)
// causes RequireJS to treat cdr_auth as a module, and therefore convincing
// RequireJS that the module must be initialized (and not just have its
// file loaded) by invoking the define(...) function's callback before
// running the innermost callback below. This guess appears to have been
// confirmed by testing, which was unable to trigger the failure when
// define(...) was used in hacks/cdr_auth.js instead of require(...).

require(['backbone'], function() {
  require(['hacks/cdr_auth'], function() {
    require([
      'jobs-view',
      'executions-view',
      'logs-view',
      'jobs-collection',
      'executions-collection',
      'logs-collection'
    ], function(
      JobsView,
      ExecutionsView,
      LogsView,
      JobsCollection,
      ExecutionsCollection,
      LogsCollection
    ) {

      'use strict';

      var jobsCollection = new JobsCollection();
      var executionsCollection = new ExecutionsCollection();
      var logsCollection = new LogsCollection();

      new JobsView({
        collection: jobsCollection
      });

      new ExecutionsView({
        collection: executionsCollection
      });

      new LogsView({
        collection: logsCollection
      });

      //
      // Initialize URL router
      //
      var AppRouter = Backbone.Router.extend({
        routes: {
          'jobs': 'jobsRoute',
          'executions': 'executionsRoute',
          'jobs/:jid': 'jobsRoute',
          'executions/:eid': 'executionsRoute',
          'logs': 'logsRoute',
          '*actions': 'defaultRoute'
        }
      });

      var switchTab = function(switchTo) {
        var pages = ['jobs', 'executions', 'logs'];
        _.each(pages, function(page) {
          $('#' + page + '-page-sidebar').hide();
          $('#' + page + '-page-content').hide();
          $('#' + page + '-tab').removeClass();
        });
        $('#' + switchTo + '-page-sidebar').show();
        $('#' + switchTo + '-page-content').show();
        $('#' + switchTo + '-tab').addClass('active');
      };

      var appRouter = new AppRouter;
      appRouter.on('route:jobsRoute', function(jobId) {
        switchTab('jobs');
        if (jobId) {
          jobsCollection.getJob(jobId);
        } else {
          jobsCollection.getJobs();
        }
      });

      appRouter.on('route:executionsRoute', function(executionId) {
        switchTab('executions');

        if (executionId) {
          executionsCollection.getExecution(executionId);
        } else {
          executionsCollection.getExecutions();
        }
      });

      appRouter.on('route:logsRoute', function() {
        switchTab('logs');
        logsCollection.getLogs();
      });

      appRouter.on('route:defaultRoute', function(actions) {
        // Anything else defaults to jobs view
        switchTab('jobs');
        jobsCollection.getJobs();
      });

      Backbone.history.start();
    });
  });
});
