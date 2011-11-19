
var countdownAction = function(count, interval, mainAction, intervalAction) {
  // inspired by http://www.tripwiremagazine.com/2011/04/9-cool-jquery-countdown-scripts.html
  // wait count intervals and then run mainAction().
  // in between intervals, run intervalAction(remaining), where remaining is the number of intervals that will be waited before mainAction()
  // e.g. if count == 3, then wait...intervalAction...wait...intervalAction...wait...mainAction.
  // e.g. if count == 1, then wait...mainAction.
  // e.g. if count == 0, then mainAction.
  // interval: in milliseconds.  
  // count: an integer >= 0. number of intervals before executing main action.
  if (count <= 0) {
    mainAction();
  } else {
    var countdown = setInterval(function() {
      count--;
      if (count <= 0) {
        clearInterval(countdown);
        mainAction()
      } else {
        intervalAction(count);
      }
    }, interval);
  }
};

var waitOnJob = function(job, url) {
  // waits, then checks to see if a lsf job is finished.  if so it forwards the browser to url.  otherwise it waits and checks again.
  // while waiting it makes little tickmarks so the user feels like something is happening.
  var msg = $("p#wait_msg").html();
  countdownAction(10, 1000, 
                  function() {
                    $.ajax({ "url": "{% url 'home.views.job_ready' %}",
                             data: {"job": job},
                             dataType: "json",
                             success: function(data) {
                                        if (data.ready) { window.location.replace(url); } 
                                        else { $("p#wait_msg").html(msg); waitOnJob(job, url); }
                                      },
                             error: function() { alert("callback failed for job="+job+" and url="+url); }
                           });},
                  function(remaining){$("p#wait_msg").html(function(index, oldhtml){ return oldhtml + "."; })});
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

function docWindow2(url) {
    var windowName = 'windowName';
    var properties = 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,copyhistory=no,width=1024,height=700';
    window.open(url, windowName, properties);
}

//Is obj in the array arr?
function inArray(obj, arr) {
  for (var i = 0; i < arr.length; i++) {
    if (arr[i] == obj) {
      return true;
    }
  }
  return false;
}


function filterSelect2(checkboxesName, selectId, optionsMap) {
    // checkboxesName: used as a selector for the checkboxes
    // selectId: the choices
    // Use check boxes to populate and filter the options in a select box.
    console.log('started');

    var filterOptions = function() {
        // console.log('filtering');
        var sel = $('#' + selectId);
        var options = [];
        sel.empty();
        $('input[name="' + checkboxesName + '"]:checked').each( function(i,elem){
                var optionsKey = $(elem).attr('value');
                options = options.concat(optionsMap[optionsKey]);
            });
        // on production, sort returns bizarre results, not at all sorted.
        // options.sort(function(opt1, opt2) { return (opt1.name.toLowerCase() > opt2.name.toLowerCase());});
        $.each(options, function(i, option){
                sel.append('<option value="' + option.value + '">' + option.name + '</option>');
            });
    };

    filterOptions();

    /** Set up responses to events ****************************************/
    /* regenerate the select dropdown when checkbox status changes */
    $('input[name="' + checkboxesName + '"]').change(filterOptions);
}


function filterSelect(checkboxesName, selectId, keyedOptions) {
    // checkboxesName: used as a selector for the checkboxes
    // selectId: the choices
    // keyedOptions: a list of tuples of (key, option)
    // Use check boxes to populate and filter the options in a select box.
    // Order of options in keyedOptions is preserved.
    console.log('started');

    var filterOptions = function() {
        console.log('filtering');
        var sel = $('#' + selectId);
        sel.empty();
        var keys = [];
        $('input[name="' + checkboxesName + '"]:checked').each(function(i, elem){
                keys.push($(elem).attr('value'));
            });
        console.log(keys);
        // on production, sort returns bizarre results, not at all sorted.
        // options.sort(function(opt1, opt2) { return (opt1.name.toLowerCase() > opt2.name.toLowerCase());});
        $.each(keyedOptions, function(i, ko){
                if ($.inArray(ko[0], keys) > -1) {
                    sel.append('<option value="' + ko[1].value + '">' + ko[1].name + '</option>');
                }
            });
    };

    filterOptions();

    /** Set up responses to events ****************************************/
    /* regenerate the select dropdown when checkbox status changes */
    $('input[name="' + checkboxesName + '"]').change(filterOptions);
}


function selectToTextarea(selectId, textareaId) {
    // selectId: the choices
    // textareaId: where the options end up. 
    // When an option is selected, it is copied to the last line of the
    // textarea, followed by a newline.
    /** Set up responses to events ****************************************/
    /* transfer selection from dropdown to text area */
    $('#' + selectId).change( function(event){
            var selected_genome = $('#' + selectId + " option:selected").attr('value');
            var previous_genomes = $('#' + textareaId).val();
            console.log('selected_genome=' + selected_genome);
            console.log('previous_genomes=' + previous_genomes);
            $('#' + textareaId).val( previous_genomes + selected_genome + '\n' );
        });
}


function tidyTextarea(textareaId){
    // When the textarea is changed, the lines in it are
    // trimmed, blank lines are removed, and a newline
    // is added to the end.
    $('#' + textareaId).change( function(){
            // console.log("textarea changed");
            var genomes = $('#' + textareaId).val().split( /\n/ );
            genomes = $.grep($.map(genomes, function(g) {return g.trim();}), 
                             function(g) {return g;});
            genomes.push("");
            $('#' + textareaId).val(genomes.join("\n"));
        });
}


