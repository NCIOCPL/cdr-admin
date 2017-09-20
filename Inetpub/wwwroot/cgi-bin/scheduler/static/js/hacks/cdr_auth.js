
/**
 * This module will override the native BackBone sync method that
 * communicates with the server adding in the necessary CDR
 * authentication token.
 * @param  {[type]} Backbone) {             } A reference to the backbone module
 * @return {[type]}           [description]
 */
require(['backbone', 'vendor/URIjs/URI'], function(Backbone, URI) {

	//A nice place to define our parameter,.
	var CDR_SESSION_PARAM = "Session";

	//Save BackBone's Sync as we will use it.
	var _BBInternalSync = Backbone.sync;

	var _internals = { };


	/**
	 * Gets the current CDR Session ID
	 * @return {[type]} [description]
	 */
	_internals.getSessionID = function () {
		var currentURI = URI(window.location.href);

		var mySessionID = "";

		if (currentURI.hasQuery(CDR_SESSION_PARAM)) {
			mySessionID = currentURI.search(true)[CDR_SESSION_PARAM];
		}

		return mySessionID;
	}

	/**
	 * Override Backbone sync to push in our CDR SESSION ID
	 * for any API request.
	 * @param  {[type]} method  [description]
	 * @param  {[type]} model   [description]
	 * @param  {[type]} options [description]
	 * @return {[type]}         [description]
	 */
	Backbone.sync = function(method, model, options) {

		//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		//NOTE: APPLY THIS LOGIC TO options.url AS WELL!!(IF SET)!!!!!!!!!!!!!!!!!
		//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

		//Basically we will modify the Model's URL to push
		//in our Query Parameter.
		if (model.url != null && model.url.trim() != "") {

			var myModelURL = URI(model.url);


			//Of the Model URL does not already have the Session parameter, then addit if it exists.
			if (!myModelURL.hasQuery(CDR_SESSION_PARAM)) {

				//Get the current session ID
				var sessionID = _internals.getSessionID();

				if (sessionID != "") {
					myModelURL.addQuery(CDR_SESSION_PARAM, sessionID);
				} else {
					//No Session, then there is a problem
					window.console && console.log('Session parameter, ' + CDR_SESSION_PARAM + ', is missing.');
				}

				model.url = myModelURL.toString();
			}
		} else {
			//No URL, bad mojo.  This may happen if the app is storing a model locally with no
			//server backend.  But then again, they should override the sync function for that model
			//specifically.
			window.console && console.log('The Model is missing a URL.');
		}

		//Call the internal function
		_BBInternalSync(method, model, options);
	};

});
