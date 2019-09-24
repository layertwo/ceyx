var R = 6378100; /* Earth radius */

var BOXWIDTH = 0; /* Selection width and height if any. Updated by showBoxSelectionInfo() call */
var BOXHEIGHT = 0;
var OBJECTCOUNT = 0; /* OSM elements within the selected area */
var OVERPASSURL = "https://lz4.overpass-api.de/api/interpreter";

function log(str) {
	if(console && console.log) {
		console.log(str);
	}
}
/**
 * Convert a longitude value to tile number
 */
function lon2tile(lon,zoom,round) {
	var t = (lon+180)/360*Math.pow(2,zoom);
	if(round) { return Math.floor(t); } else { return t; }
}

/**
 * Convert a latitude value to tile number
 */
function lat2tile(lat,zoom,round) {
	var t = (1-Math.log(Math.tan(lat*Math.PI/180) + 1/Math.cos(lat*Math.PI/180))/Math.PI)/2 *Math.pow(2,zoom);
	if(round) { return Math.floor(t); } else { return t; }
}

/**
 * Convert a tile to longitude
 */
function tile2lon(x,z) {
	return (x/Math.pow(2,z)*360-180);
}

/**
 * Convert a tile to latitude
 */
function tile2lat(y,z) {
	var n=Math.PI-2*Math.PI*y/Math.pow(2,z);
	return (180/Math.PI*Math.atan(0.5*(Math.exp(n)-Math.exp(-n))));
}

/**
 * Calcualtes the distance in meters - Mercator projection - between two latitutde values
 */
function latDistance(lat1, lat2) {
	var rad1 = lat1*(Math.PI/180);
	var rad2 = lat2*(Math.PI/180);
	var y1 = Math.log( (1 + Math.sin(rad1)) / Math.cos(rad1) ) * R;
	var y2 = Math.log( (1 + Math.sin(rad2)) / Math.cos(rad2) ) * R;
	return Math.round(Math.abs(y1 - y2));
}

/**
 * Calcualtes the distance in meters - Mercator projection - between two longitude values
 */
function lonDistance(lon1, lon2) {
	var rad1 = lon1*(Math.PI/180);
	var rad2 = lon2*(Math.PI/180);
	return Math.round(Math.abs(rad1 - rad2) * R);
}


/**
 * Round a number to the specified decimal digits
 */
function roundNumber(num, dec) {
	var result = Math.round(num*Math.pow(10,dec))/Math.pow(10,dec);
	return result;
}

// Parse query string parameters into an array
// http://javascript.about.com/library/blqs1.htm
function qs(url) {
	var qsParm = new Array();
	if(url.indexOf('?') > -1) {
		//var query = window.location.search.substring(1);
		var query = url.split('?',2)[1];
		var parms = query.split('&');
		for (var i=0; i<parms.length; i++) {
			var pos = parms[i].indexOf('=');
			if (pos > 0) {
				var key = parms[i].substring(0,pos);
				var val = parms[i].substring(pos+1);
				qsParm[key] = val;
			}
		}
	}
	return qsParm;
} 

/**
 * Remove box selection from the current URL and return it without that part
 */
function removeSelectionFromUrl(url) {
	if(url.indexOf('?') == -1) {
		return url;
	}
	var script = url.split('?',2)[0] + "?";
	var q = qs(url);
	var result = "";

	// Remove selection from query
	for(var v in q) {
		if(v != "box") {
			result += v + "=" + q[v] + "&";
		}
	}
	return script + result.substring(0, result.length - 1);
}
/** 
 * Replace box selection in the URL and return new URL
 * Or remove box= part if no selection
 */
function addBoxToUrl(url) {
	var result = removeSelectionFromUrl(url);

	var lat1 = document.getElementById("selectlat1").value;
	var lon1 = document.getElementById("selectlon1").value;
	var lat2 = document.getElementById("selectlat2").value;
	var lon2 = document.getElementById("selectlon2").value;

	if(lat1 && lon1 && lat2 && lon2) {
		result += "&box=" 
		+ roundNumber(lat1, 5) + "," + roundNumber(lon1, 5) + "," 
		+ roundNumber(lat2, 5) + "," + roundNumber(lon2, 5);
	}
	return result;
}

/**
 * Add the selection box to a link object on the screen
 */
function addBoxToLink(linkID, lat1, lon1, lat2, lon2) {
	var link = document.getElementById(linkID);
	// Some controls may be invisible (e.g. zoom in on max zoom)
	if(link) {
		link.href = addBoxToUrl(link.href, lat1, lon1, lat2, lon2);
	}
}
/**
 * Recreate box selection
 */
function reselect(lat1, lon1, lat2, lon2) {

	if(lat1 != lat2 && lon1 != lon2) {
		
		var b = new OpenLayers.Bounds(
			lon1 < lon2 ? lon1 : lon2,
			lat1 < lat2 ? lat1 : lat2,
			lon1 < lon2 ? lon2 : lon1,
			lat1 < lat2 ? lat2 : lat1);
		b.transform("EPSG:4326", map.projection);

		var poly = new OpenLayers.Feature.Vector(b.toGeometry());
		vectors.addFeatures([poly]);
		goEditMode();

		showBoxSelectionInfo(lat1, lon1, lat2, lon2);
	}
}

/**
 * Store passed selection area to FORM HIDDEN fields for submit
 */
function storeSelection(lat1, lon1, lat2, lon2) {
	document.getElementById("selectlat1").value = lat1;
	document.getElementById("selectlon1").value = lon1;
	document.getElementById("selectlat2").value = lat2;
	document.getElementById("selectlon2").value = lon2;

	showBoxSelectionInfo(lat1, lon1, lat2, lon2);
}

/**
 * Show a message to the user about currently selected box area 
 * Also updates BOXWIDTH and BOXHEIGHT globals.
 */
function showBoxSelectionInfo(lat1, lon1, lat2, lon2) {
	BOXHEIGHT = latDistance(lat1, lat2);
	BOXWIDTH = lonDistance(lon1, lon2);
	OBJECTCOUNT = 0;
	var square_km = Math.round((BOXHEIGHT/1000) * (BOXWIDTH/1000),1);
	var pages = $("#pagesselect").val().split("x");
	pages = parseInt(pages[0]) * parseInt(pages[1]);

	$(".clientrender").show();
	$("#clientinfo").html("Selection: " 
			+ Math.round(BOXWIDTH/100)/10 + " x " 
			+ Math.round(BOXHEIGHT/100)/10 + " km." +
			(square_km < MAX_SQUARE_KM && square_km / pages > 1 ? " <span class=\"error\">Selection might be too big for usable print result (detail survey!) or needs more pages.</span>" : "") +
			(square_km > MAX_SQUARE_KM ? " <span class=\"error\">Bigger than allowed " + MAX_SQUARE_KM + " square kilometers.</span>" : ""));
	var bbox = lat1 + "," + lon1 + "," + lat2 + "," + lon2;

	// Query number of OSM elements in the selected area
	$.ajax(OVERPASSURL, {
			data: { data: "[out:json][timeout:25];(node(" + bbox + "););out count;>;out count;" },
			success: function(res, textStatus, jqXHR) {
				var elems = 0;
				// Parse "count" result from Overpass API
				if(res.elements && res.elements.length > 0) {
					for(var i = 0; i < res.elements.length; i++) {
						if(res.elements[i].tags) {
							elems += Number(res.elements[i].tags.total);
						}
					}
				}
				log(elems);
				OBJECTCOUNT = elems;
				if(OBJECTCOUNT/pages > MAX_OBJ_PER_PAGE) {
				$("#clientinfo").append("<p class=\"error\">Selected " + OBJECTCOUNT + " OSM nodes" 
					+ ". Please select smaller area or more papers. Maximum: " 
					+ MAX_OBJ_PER_PAGE + " nodes per page.</p>");
					$("#submit").prop("disabled", true);
				} else {
					$("#submit").prop("disabled", false)
				}
			}
		});
}


function deleteSelection() {
	javascript:document.location.href = removeSelectionFromUrl(document.getElementById('permalink').href);
}

function centerSelection() {
	var f = vectors.features[0];
	var center = f.geometry.getCentroid();
	var lonLat = center.transform(map.displayProjection, map.projection);
	map.moveTo(center); // FIXME
}

/**
 * Run a search or jumping to OSM-permalink
 */
function doJump() {
	var q = document.getElementById("q").value;

	if(q == "") { return false; }

	if(q.match("https?://")) {
		return true; // OSM permalink, pass to old PHP function
	}

	var url = 'https://nominatim.openstreetmap.org/search?q=' 
		+ encodeURIComponent(q) + '&format=json&addressdetails=0&email=info@openstreetmap.hu&accept-language=hu';
	$.get(url, function(data) {

		if(typeof(data) == "string") {
			data = $.parseJSON(data); // Firefox does this, dunno why
		}
		// Show search results
		$("#results").empty();
		var count = 0;
		var lastUrl = "";
		for(var i = 0; i < data.length; i++) {
			if(data[i].class != "place" && data[i].class != "boundary") { 
				continue; 
			}
			var x = lon2tile(Number(data[i].lon), 14, true) - 1;
			var y = lat2tile(Number(data[i].lat), 14, true) - 1;
			lastUrl = 'index.php?lat=' + data[i].lat + '&lon=' + data[i].lon + '&zoom=14';
			$("#results").append('<li><a href="' + lastUrl + '">' + data[i].display_name + '</a></li>');
			count++;
		}
		if(!count) {
			$("#results").append('<li>No match (places only)</li>');
		}
		if(count == 1) {
			document.location.href = lastUrl;
		}
	});
	return false;

}

var maxcount = 0; // Just to stop "stupid" JS somewhere
var laststatus = "";

// Started at render submit and calls itself repeatedly: displays status from Ajax call.
function showRenderStatus(id) {

	var url = "checkjob.php?id=" + id;

	$.get(url, function(data) {
		if(typeof(data) == "string") {
			data = $.parseJSON(data); // Firefox does this for nominatim (not here), dunno why
		}
		if(data.job != "ready" && data.job != "fail") {
			// Show progress and status
			if(data.job != laststatus) {
				switch(data.job) {
					case "waiting":
						$("#renderstatus").html("Waiting");
						break;
					case "working":
						$("#renderstatus").html("Working");
						break;
				}
			}
			// One space non NBSP, so it can break to lines
			if(Math.round(maxcount / 2) == (maxcount / 2)) {
				$("#progressbar").append(" ");
			} else {
				$("#progressbar").append("&nbsp;");
			}

			maxcount++;
			if(maxcount < 1000) {
				setTimeout(function() { showRenderStatus(id); }, 500);
			} else {
				$("#renderstatus").html("<b>Status: Undefined!</b>");
			}
		} else if(data.job == "fail") {
			// Render fail
			$("#renderstatus").html("<b>Failed!</b>");
			$("#rendernote").html("");
			$("#progressbar").html("");
			$("#joblink")[0].href="output/" + id + ".txt";
			$("div.jobpassed").addClass("jobfailed").removeClass("jobpassed");
		} else {
			// Ready
			$("#renderstatus").html("<b>Ready!</b>");
			$("#rendernote").html("");
			$("#progressbar").html("");
		}
	});
}

/* OpenLayers stuff */
var map, vectors, controls;
function initMap(lat, lon, zoom) {
    
	var args = OpenLayers.Util.getParameters();
	if(!lat) { lat = Number(args["lat"]); }
	if(!lat) { lat = 48.2; }
	if(!lon) { lon = Number(args["lon"]); }
	if(!lon) { lon = 19.6; }
	if(!zoom) { zoom = Number(args["zoom"]); }
	if(!zoom) { zoom = 14; }

	OpenLayers.Feature.Vector.style['default']['strokeWidth'] = '2';
	vectors = new OpenLayers.Layer.Vector("Vector Layer", {
                renderers: OpenLayers.Layer.Vector.prototype.renderers,
				projection: "EPSG:3857"
            });

		 // http://openlayers.org/dev/examples/modify-feature.html
		vectors.events.on({
			//"beforefeaturemodified": report,
			"featuremodified": report,
			//"afterfeaturemodified": report,
			//"vertexmodified": report,
			//"sketchmodified": report,
			//"sketchstarted": report,
			"sketchcomplete": report
		});
		controls = {
			regular: new OpenLayers.Control.DrawFeature(vectors,
				OpenLayers.Handler.RegularPolygon,
					{handlerOptions: {sides: 4, irregular: true}}),
			modify: new OpenLayers.Control.ModifyFeature(vectors,
				{mode: OpenLayers.Control.ModifyFeature.RESHAPE 
					| OpenLayers.Control.ModifyFeature.RESIZE
					| OpenLayers.Control.ModifyFeature.DRAG})
		};
            
/*      // The overlay layer for our marker, with a simple diamond as symbol
    var overlay = new OpenLayers.Layer.Vector('Overlay', {
        styleMap: new OpenLayers.StyleMap({
            externalGraphic: '../img/marker.png',
            graphicWidth: 20, graphicHeight: 24, graphicYOffset: -24,
            title: '${tooltip}'
        })
    });
*/
    // The location of our marker and popup. We usually think in geographic
    // coordinates ('EPSG:4326'), but the map is projected ('EPSG:3857').
    var myLocation = new OpenLayers.Geometry.Point(lon, lat)
        .transform('EPSG:4326', 'EPSG:3857');

/*    // We add the marker with a tooltip text to the overlay
    overlay.addFeatures([
        new OpenLayers.Feature.Vector(myLocation, {tooltip: 'OpenLayers'})
    ]);
*/
/*    // A popup with some information about our location
    var popup = new OpenLayers.Popup.FramedCloud("Popup", 
        myLocation.getBounds().getCenterLonLat(), null,
        '<a target="_blank" href="http://openlayers.org/">We</a> ' +
        'could be here.<br>Or elsewhere.', null,
        true // <-- true if we want a close (X) button, false otherwise
    );
*/
	var osm = new OpenLayers.Layer.OSM();

    // Finally we create the map
    map = new OpenLayers.Map({
        div: "map", 
		projection: new OpenLayers.Projection("EPSG:900913"),
		displayProjection: new OpenLayers.Projection("EPSG:4326"),
      	center: myLocation.getBounds().getCenterLonLat(), 
		eventListeners: {
			"move": map_move,
			"zoomend": map_move
		}
    });
	map.addLayers([osm, vectors]); // Need to go separately, not in options array, as that results in late creation of "map"
	map.zoomTo(zoom); // Must be set separately if "layers" is set seprately.

    // and add the popup to it.
    //map.addPopup(popup);
          for(var key in controls) {
                map.addControl(controls[key]);
            }
}
// Goes into drawing selection box mode
function goCreateMode() {
	if(vectors.features.length == 0 || confirm("Delete current selection box?\n\nYou can click it to activate modify mode.")) {
		vectors.removeAllFeatures();
		controls.modify.deactivate();
		controls.regular.activate();
		$("#map").css("cursor", "crosshair");
	}
}

// Goes into editing selection mode, deactiaves creating new box
function goEditMode() {
	controls.regular.deactivate();
	controls.modify.activate();
}

function report(event) {
	log(event.type, event.feature ? event.feature.id : event.components);

	// On finished drawing selection or modifying selection
	// "sketchcomplete" and "featuremodified"
	if(event.feature) {
		$("#map").css("cursor", "");
		var b = new OpenLayers.Bounds(event.feature.geometry.getBounds().toArray());
		b.transform(map.projection, "EPSG:4326");
		storeSelection(roundNumber(b.bottom, 6), roundNumber(b.left, 6), roundNumber(b.top, 6), roundNumber(b.right, 6));
		updateUrls();
	} else {
		log("no feature in event");
	}

	// On finished drawing the selection box
	if(event.type == "sketchcomplete" && event.feature) {
		goEditMode();
	}
}

// Move + Zoom event listener
function map_move () {
	updateUrls();
}

// Read currently selected area and show the size (and errors if any)
function updateSelectedAreaInfo() {
	if(vectors.features && vectors.features[0]) {
		var b = new OpenLayers.Bounds(vectors.features[0].geometry.getBounds().toArray());
		b.transform(map.projection, "EPSG:4326");
		showBoxSelectionInfo(roundNumber(b.bottom, 6), roundNumber(b.left, 6), roundNumber(b.top, 6), roundNumber(b.right, 6));
	} else {
		BOXWIDTH = 0;
		BOXHEIGHT = 0;
	}
}

// Update form action and permalink to store current position and selection
function updateUrls() {
	var center = map.getCenter().clone();
	var zoom = map.getZoom();
	center.transform(map.getProjectionObject(), new OpenLayers.Projection("EPSG:4326"));

	var dig = 100000; // round digits
	var lon = Math.round(center.lon * dig)/dig;
	var lat = Math.round(center.lat * dig)/dig;
	var query = "zoom="+zoom+"&lat="+lat+"&lon="+lon;
	document.getElementById("osmlink").href = "https://www.openstreetmap.org/?" + query;
	query = addBoxToUrl(query); // Add selection if any
	document.getElementById("renderForm").action = "index.php?" + query;
	document.getElementById("permalink").href = "index.php?" + query;

	// Update zoom hints
	$("#currentzoom").html("z:" + zoom);
}

function checkRenderForm() {
	updateSelectedAreaInfo();
	if(BOXWIDTH && BOXHEIGHT) {

		// Calculate per paper width and height requirement 
		var pages = $("#pagesselect").val().split("x");
		var page_w = BOXWIDTH / pages[0];
		var page_h = BOXHEIGHT / pages[1];

		// landscape or portrait paper, bloody simple check
		var paper = $("#paperselect").val();
		var askuser = false;
		if(paper == "a4l" || paper == "letterl") {
			askuser = (page_w < page_h);
		} else {
			askuser = (page_w > page_h);
		}
		if(askuser) {
			return confirm("Paper aspect ratio is opposite of your selection. Continue?\n\nYou may want to select different paper orientation or divide to pages or still print this way.");
		}
		return true;
	} else {
		alert("There is no selection. Use 'Draw box' first.");
		return false;
	}
}
