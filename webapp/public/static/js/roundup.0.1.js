
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


$(document).ready( function(){
        /** check that everything is working **/
        
        populateGenomeDropdown();
        
        /** Set up responses to events ****************************************/
        /* transfer selection from dropdown to text area */
        $('#id_genome_choices').change( function(event){
                var selected_genome = $("select#id_genome_choices option:selected").attr('value');
                var previous_genomes = $('#id_genomes').val();
                $('#id_genomes').val( previous_genomes + selected_genome + '\n' );
            });
        /* regenerate the select dropdown when checkbox status changes */
        //$('#id_genome_checkboxes input').change( populateGenomeDropdown );
        $('#id_genome_checkboxes input').change( makeCheckboxFillDropdown('#id_genome_checkboxes', '#id_genome_choices', cat_to_genomes) );
        /* tidy typing in the textarea (only after textarea loses focus) */
        $('#id_genomes').change( function(){
                console.log("textarea changed")
                    genomes = $('#id_genomes').val().split( /\n/ );
                genomes = $.grep($.map(genomes, function(g) {return g.trim();}), 
                                 function(g) {return g;});
                genomes.push("");
                $('#id_genomes').val(genomes.join("\n"));
            });
        /* monitor textarea */
        //$('#id_genomes').live('keyup', function(){ console.log('key pressed');} );
        
        /** populate the select dropdown based on options corresponding to the checked boxes **/
        function makeCheckboxFillDropdown(checkboxesId, selectId, optionsMap) {
            return function() {
                var sel = $(selectId);
                sel.empty();
                $(checkboxesId + ' input:checked').each( function(i,elem){
                        var optionKey = $(elem).attr('value');
                        $.each( optionsMap[optionsKey], function(i,option) {
                                sel.append('<option value="' + option.value + '">' + option.name + '</option>');
                            });
                    });
            };
        }

        function populateGenomeDropdown() {
            var gc = $('#id_genome_choices');
            gc.empty();
            $('#id_genome_checkboxes input:checked').each( function(i,elem){
                    var genome_set = $(elem).attr('value');
                    $.each( cat_to_genomes[genome_set], function(i,option) {
                            gc.append('<option value="' + option.value + '">' + option.name + '</option>');
                        });
                });
        }

    });

//keep in mind for later:
//disable a form element:
//$('x').attr('disabled', true);

