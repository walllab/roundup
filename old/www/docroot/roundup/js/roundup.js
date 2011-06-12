// FUNCTIONS FROM http://www.dustindiaz.com/top-ten-javascript/
// TOP TEN JAVASCRIPT FUNCTIONS

function addEvent(elm, evType, fn, useCapture) {
        if (elm.addEventListener) {
		elm.addEventListener(evType, fn, useCapture);
		return true;
	}
	else if (elm.attachEvent) {
		var r = elm.attachEvent('on' + evType, fn);
		return r;
	}
	else {
		elm['on' + evType] = fn;
	}
}

// func: a function object which takes no parameters.  
// replaces the current onload event of html document with a function that calls the current onload function and then func.
// If you need parameters for your function, create an anonymous closure (a.k.a. a lambda) around them,
// e.g. addLoadEvent(function(){myFunc(param1, param2);});
// Note: useful to add an event when the body tag is not accessible, perhaps because it is declared in a header file.
function addLoadEvent(func) {
	var oldonload = window.onload;
	if (typeof window.onload != 'function') {
		window.onload = func;
	}
	else {
		window.onload = function() {
			oldonload();
			func();
		}
	}
}

// Can also use addEvent to do the same thing as addLoadEvent.
// addEvent(window,'load',func1,false);
// addEvent(window,'load',func2,false);
// addEvent(window,'load',func3,false);


function getElementsByClass(searchClass,node,tag) {
	var classElements = new Array();
	if ( node == null )
		node = document;
	if ( tag == null )
		tag = '*';
	var els = node.getElementsByTagName(tag);
	var elsLen = els.length;
	var pattern = new RegExp("(^|\\s)"+searchClass+"(\\s|$)");
	for (i = 0, j = 0; i < elsLen; i++) {
		if ( pattern.test(els[i].className) ) {
			classElements[j] = els[i];
			j++;
		}
	}
	return classElements;
}


function toggleDisplay(elemId) {
	var el = document.getElementById(elemId);
	if ( el.style.display != 'none' ) {
		el.style.display = 'none';
	}
	else {
		el.style.display = '';
	}
}


function insertAfter(parent, node, referenceNode) {
	parent.insertBefore(node, referenceNode.nextSibling);
}


Array.prototype.inArray = function (value) {
	var i;
	for (i=0; i < this.length; i++) {
		if (this[i] === value) {
			return true;
		}
	}
	return false;
};


function getCookie( name ) {
	var start = document.cookie.indexOf( name + "=" );
	var len = start + name.length + 1;
	if ( ( !start ) && ( name != document.cookie.substring( 0, name.length ) ) ) {
		return null;
	}
	if ( start == -1 ) return null;
	var end = document.cookie.indexOf( ";", len );
	if ( end == -1 ) end = document.cookie.length;
	return unescape( document.cookie.substring( len, end ) );
}
	
function setCookie( name, value, expires, path, domain, secure ) {
	var today = new Date();
	today.setTime( today.getTime() );
	if ( expires ) {
		expires = expires * 1000 * 60 * 60 * 24;
	}
	var expires_date = new Date( today.getTime() + (expires) );
	document.cookie = name+"="+escape( value ) +
		( ( expires ) ? ";expires="+expires_date.toGMTString() : "" ) +
		( ( path ) ? ";path=" + path : "" ) +
		( ( domain ) ? ";domain=" + domain : "" ) +
		( ( secure ) ? ";secure" : "" );
}
	
function deleteCookie( name, path, domain ) {
	if ( getCookie( name ) ) document.cookie = name + "=" +
			( ( path ) ? ";path=" + path : "") +
			( ( domain ) ? ";domain=" + domain : "" ) +
			";expires=Thu, 01-Jan-1970 00:00:01 GMT";
}


function createCookie(name,value,days)
{
	if (days)
	{
		var date = new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		var expires = "; expires="+date.toGMTString();
	}
	else var expires = "";
	var ck = name+"="+value+expires+"; path=/";
	if (days != -1) alert('Cookie\n' + ck + '\ncreated');
	document.cookie = ck;
}

function readCookie(name)
{
	var nameEQ = name + "=";
	var ca = document.cookie.split(';');
	for(var i=0;i<ca.length;i++)
	{
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1,c.length);
		if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
	}
	return null;
}

function eraseCookie(name)
{
	createCookie(name,"",-1);
}


function $() {
	var elements = new Array();
	for (var i = 0; i < arguments.length; i++) {
		var element = arguments[i];
		if (typeof element == 'string')
			element = document.getElementById(element);
		if (arguments.length == 1)
			return element;
		elements.push(element);
	}
	return elements;
}
	
// Sample Usage:
//var obj1 = document.getElementById('element1');
//var obj2 = document.getElementById('element2');
//function alertElements() {
//  var i;
//  var elements = $('a','b','c',obj1,obj2,'d','e');
//  for ( i=0;i<elements.length;i++ ) {
//    alert(elements[i].id);
//  }
//}


function foreach(arr, func) {
  for (var i = 0; i < arr.length; i++) {
	func(arr[i]);
  }
}


// DEPRECATED: USE addLoadEvent()
// func: a function object which takes no parameters.  
// replaces the current onload event of html document with a function that calls the current onload function and then func.
// If you need parameters for your function, create an anonymous closure (a.k.a. a lambda) around them,
// e.g. appendOnLoadEvent(function(){myFunc(param1, param2);});
// You can also add user defined functions, like so:
// function myfunc() { alert('hi'); }
// appendOnLoadEvent(myfunc);
// This function can be used to add a function to the onload event of the <body> tag, when you do not have access to the body tag.
//function appendOnLoadEvent(func) {
//  var oldLoad = window.onload;
//  if (oldLoad) {
//    window.onload = function(){ oldLoad(); func(); };
//  } else {
//    window.onload = func;
//  }
//}


//Is obj in the array arr?
function inArray(obj, arr) {
  for (var i = 0; i < arr.length; i++) {
    if (arr[i] == obj) {
      return true;
    }
  }
  return false;
}


// item: any kind of variable, possibly an array.
// returns: item if it is an array, or item wrapped in an array if it is not.
function makeIntoArray(item) {
    if ((typeof item == "object") && (item.constructor == Array)) { 
	return item;
    } else {
	return [item];
    }
}


//
// FORM UTILITY FUNCTIONS
//

// form: form element
// values: map of element name to a value or an array of values in the case of select or checkbox elements.
// goes through the form elements, assigning their value to the one mapped in values, or checking or selecting
// the element (or its option) if the values match in the case of checkboxes, radio buttons, and selects.
function setFormValues(form, values) {
  form.reset();
  for (var i = 0; i < form.elements.length; i++) {
    var elem = form.elements[i];
    var value = values[elem.name];
    if (typeof value == "undefined") {
	continue;
    }
    if (elem.type == null) {
        continue;
    } else if (elem.type == "select-one" || elem.type == "select-multiple") {
	var valueArr = makeIntoArray(value);
	for (var j = elem.options.length - 1; j >= 0; j--) {
	    if (inArray(elem.options[j].value, valueArr)) {
		elem.options[j].selected = true;
	    } else {
		elem.options[j].selected = false;
            }
        }
    } else if (elem.type == "checkbox" || elem.type == "radio") {
	var valueArr = makeIntoArray(value);
	if (inArray(elem.value, valueArr)) {
	    elem.checked = true;
	} else {
	    elem.checked = false;
        }
    } else {
	elem.value = value;
    }
  }
}



//
// XMLHTTPREQUEST OBJECT AND AJAX LIBRARY FUNCTIONS
//


/*
 * Source: http://www-128.ibm.com/developerworks/library/j-ajax1/?ca=dgr-lnxw01Ajax
 * Returns a new XMLHttpRequest object, or false if this browser
 * doesn't support it
 */
function newXMLHttpRequest() {

  var xmlreq = false;

  if (window.XMLHttpRequest) {

    // Create XMLHttpRequest object in non-Microsoft browsers
    xmlreq = new XMLHttpRequest();

  } else if (window.ActiveXObject) {

    // Create XMLHttpRequest via MS ActiveX
    try {
      // Try to create XMLHttpRequest in later versions
      // of Internet Explorer

      xmlreq = new ActiveXObject("Msxml2.XMLHTTP");

    } catch (e1) {

      // Failed to create required ActiveXObject

      try {
        // Try version supported by older versions
        // of Internet Explorer

        xmlreq = new ActiveXObject("Microsoft.XMLHTTP");

      } catch (e2) {

        // Unable to create an XMLHttpRequest with ActiveX
      }
    }
  }

  return xmlreq;
}


/*
 * Returns a function that, when called with an XMLHttpRequest obj, returns a 
 * function that waits for the specified XMLHttpRequest
 * to complete, then passes the XML response to one handler function on success
 * or the request object to another handler on failure.
 * req - The XMLHttpRequest whose state is changing
 * successHandler - Function passed request object when return status == 200.
 * httpErrorHandler - function passed XMLHttpRequest object when return status != 200.  Defaults to showing a simple alert box on error.
 */
function getReadyStateHandlerMaker(successHandler, httpErrorHandler) {
  return function(req) {
    httpErrorHandler = (typeof httpErrorHandler == "undefined") 
      ? function (req) { alert("HTTP error status: "+req.status); }
      : httpErrorHandler; 

    // Return an anonymous function that listens to the 
    // XMLHttpRequest instance
    return function () {
      // If the request's status is "complete"
      if (req.readyState == 4) {
        // Check that a successful server response was received
        if (req.status == 200) {
          // Pass the XML payload of the response to the 
          // handler function
          // alert('req.responseText='+req.responseText);
          successHandler(req);
        } else {
          // An HTTP problem has occurred
          httpErrorHandler(req);
        }
      }
    }
  }
}


// url: location of request
// callbackMaker: function passed XMLHttpRequest obj which must return a function which is called on ready state change of request
// data: form encoded data to send along with request
// method: e.g. "POST", "GET", "HEAD", ....  Defaults to "POST".
// contentType: set Content-Type header.  Defaults to "application/x-www-form-urlencoded".
// isAsync: whether or not to process the request synchronously or asynchronously.  Defaults to true.
// Helper function which submits XMLHttpRequest and lets callback handle the results.
// returns: nothing.  request handled by callback instead.
function sendXMLHttpRequest(url, callbackMaker, data, method, contentType, isAsync) {
  // default values
  method = (typeof method == "undefined") ? "POST" : method; 
  isAsync = (typeof isAsync == "undefined") ? true : isAsync; 
  contentType = (typeof contentType == "undefined") ? "application/x-www-form-urlencoded" : contentType; 

  // Obtain an XMLHttpRequest instance
  var req = newXMLHttpRequest();

  // set handler of request
  req.onreadystatechange = callbackMaker(req);

  // Third parameter specifies request is asynchronous.
  req.open(method, url, isAsync);

  // Specify that the body of the request contains form data
  req.setRequestHeader("Content-Type", contentType);

  // Send form encoded data.
  req.send(data);
}



//
// e.g. <error><error_code>1</error_code><error_message>Bad Input!</error_message></error>
//
function isErrorXML(xml) {
	kids = xml.childNodes;
	if (kids.length == 1) {
		root = kids[0];
		if (root.nodeType == 1 && root.tagName.toLowerCase() == 'error') { //1 == ELEMENT_NODE
			return true;
		}
	}
	return false;
}


function parseErrorXML(xml) {
	if (isErrorXML(xml)) {
		errorNode = xml.childNodes[0];
		codeNode = errorNode.getElementsByTagName('error_code')[0];
		messageNode = errorNode.getElementsByTagName('error_message')[0];
		code = codeNode.firstChild.data;
		message = messageNode.firstChild.data;
		return {code: code, message: message};
	} else {
		return {code: -1, message: 'Error parsing error'};
	}
}




// id: corresponds to the name of the documentation page that get_doc.php will retrieve without the '.php' extension
// anchor: if specified, will be added to the url.  should refer to an anchor in the documentation page.
function docWindow(id, anchor) {
	anchorUrlFrag = (typeof anchor == "undefined") ? '' : '#'+anchor;
	url = '/roundup/docs/get_doc.php?id='+id+anchorUrlFrag;
	RodeoInfo(url,'windowName','toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,copyhistory=no,width=660,height=540');
}

function RodeoInfo(filename,windowname,properties) {
    mywindow = window.open(filename,windowname,properties);
}

