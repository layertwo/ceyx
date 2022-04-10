<?php
/*
 * render(myMap) - (c)2011-2018 Ferenc Veres
 * Licensed under GPL v3
 */
session_start();
include 'header.php';
include 'lib.php';
?>
<div id="content">
<div id="map">
</div>

<div id="panels">

<?php
$map = new MapSettings();
$ok = false;
if(array_key_exists("osmlink", $_POST)) {
	$ok = $map->readFromPermaLink($_POST["osmlink"]);
} else {
	$ok = $map->readFromQuery();
}
if(!$ok) {
	// Default view if no cool input
	$map->CenterLat = 47.51627321168;
	$map->CenterLon = 19.054412841797;
	$map->Zoom = 3;
}

// Process render
if(array_key_exists("render", $_POST)) {
	$jobid = false;
	// Capcha check
	if(!array_key_exists('code', $_POST)
		|| !array_key_exists('code', $_SESSION)
		|| $_POST["code"] != $_SESSION["code"]) {
		echo "CAPTHCA validation code didn't match.";
	} else {
 		$jobid = $map->submitRender();
	}
	if($jobid !== false) {
?>
<div class="jobpassed">
<h1>Processing....</h1>
<p>Your map have been passed to the renderer. <strong>Wait</strong> for
it to be complete.</p>
<p><strong>Job ID: <a id="joblink" href="output/<?php echo($jobid); ?>/<?php echo($jobid); ?>.html" target="_blank"><?php echo($jobid); ?></a></strong> 
<span id="renderstatus">Working</span>
<span id="progressbar"></span>
<em id="rendernote">(404 if you click fast)</em></p>
		<script type="text/javascript">
			showRenderStatus("<?php echo($jobid); ?>");
		</script>
</div>
<?php
	} else {
?>
<div class="jobfailed">
<h1>Error...</h1>
Job failed, with a reason visible above...
</div>
<?php
	}
}

?>
<!-- Title panel -->
<div class="panel">
 
<h2>render(myMap) <span class="beta">beta</span><br/></h2>
<p>Prints predefined style OpenSteetMap maps for detail mapping (not Mapnik tiles).
<strong>[<a href="help.html">help</a>]</strong>
<strong>[<a href="news.html">news</a>]</strong></p>
</div>

<!-- Permalink loader panel -->
	<form action="index.php" method="post" class="panel">
	<h2>Search</h2>
	Search or OSM permalink:<input type="text" id="q" name="osmlink" value="" title="Type a city name here or paste an OSM permalink to jump to."/>
	<input type="submit" value="Search/Jump" onclick="return doJump();"/>
	<a id="osmlink" href="<?php echo($map->getLink("osm")); ?>" target="_blank" title="Opens the current view on OSM in new window.">Open on OSM</a>

	<ul id="results">
	</ul>
	</form>


<?php 
// Renderer panel, if selection has size
// Form data to unsafe strings
$ustyle = "";
$upages = "";
$upaper = "";
$unotes = "";
$udetailzoom = "";
if(array_key_exists("style", $_POST)) { $ustyle = $_POST["style"]; }
if(array_key_exists("pages", $_POST)) { $upages = $_POST["pages"]; }
if(array_key_exists("paper", $_POST)) { $upaper = $_POST["paper"]; }
if(array_key_exists("notes", $_POST)) { $unotes = $_POST["notes"]; }
if(array_key_exists("detailzoom", $_POST)) { $udetailzoom = $_POST["detailzoom"]; }

?>
<form id="renderForm" action="<?php echo($map->getLink("")); ?>" method="post" class="panel" onsubmit="return checkRenderForm();">
<input type="hidden" name="selectlat1" id="selectlat1" value="<?php echo($map->SelectLat1); ?>" />
<input type="hidden" name="selectlon1" id="selectlon1" value="<?php echo($map->SelectLon1); ?>" />
<input type="hidden" name="selectlat2" id="selectlat2" value="<?php echo($map->SelectLat2); ?>" />
<input type="hidden" name="selectlon2" id="selectlon2" value="<?php echo($map->SelectLon2); ?>" />
<h2>Rendering job
<span style="display: block; float: right; padding: 0 4px; font-size: 100%; font-weight: normal;" id="currentzoom">z:<?php echo($map->Zoom); ?></span></h2>
<p style="font-weight: bold;">Start: <input type="button" onclick="goCreateMode()" value="Draw box" title="Click this and drag a box around the area you want to print. Then you can adjust the box." />
| <!-- a title="Center selection" href="javascript:centerSelection();">C</a> | -->
<a title="Delete selection" href="javascript:deleteSelection();">Del</a>
</p>

<p class="clientrender important" id="clientinfo">Render info...</p>
<p style="margin-bottom: 0;">
	Divide to pages: <select id="pagesselect" name="pages" title="Make sure to divide to enough pages based on area size and density, otherwise labels will overlap!" onchange="updateSelectedAreaInfo();">
	<option value="1x1"<?php sel($upages == "1x1"); ?>>  1</option>
	<option value="2x1"<?php sel($upages == "2x1"); ?>>2x1</option>
	<option value="3x1"<?php sel($upages == "3x1"); ?>>3x1</option>
	<option value="1x2"<?php sel($upages == "1x2"); ?>>1x2</option>
	<option value="2x2"<?php sel($upages == "2x2"); ?>>2x2</option>
	<option value="3x2"<?php sel($upages == "3x2"); ?>>3x2</option>
	<option value="1x3"<?php sel($upages == "1x3"); ?>>1x3</option>
	<option value="2x3"<?php sel($upages == "2x3"); ?>>2x3</option>
	<option value="3x3"<?php sel($upages == "3x3"); ?>>3x3</option>
	</select><br/>
<table style="width: 100%">
<tr><th>Paper:</th>
<td><select id="paperselect" name="paper" title="Selects image width. Aspect ratio to fit in height is up to your guess or print preivew!">
<option value="a4p"<?php sel($upaper == "a4p"); ?>>A4 portrait</option>
<option value="a4l"<?php sel($upaper == "a4l"); ?>>A4 landscape</option>
<option value="letterp"<?php sel($upaper == "letterp"); ?>>Letter portrait</option>
<option value="letterl"<?php sel($upaper == "letterl"); ?>>Letter landscape</option>
</select></td></tr>
<tr><th>Content:</th>
<td><select name="style" title="Selects which objects to prefer in output.">
	<option value="shops"<?php sel($ustyle == "shops"); ?>>Shops, POIs</option>
	<option value="housenumbers"<?php sel($ustyle == "housenumbers"); ?>>House numbers</option>
	<option value="wheelchair"<?php sel($ustyle == "wheelchair"); ?>>Wheelchair</option>
</select></td></tr>
<tr><th>Detail:</th>
<td><select name="detailzoom" id="detailzoom" title="Selects how detailed the printed information should be. See help for details."  onchange="updateSelectedAreaInfo();">
<option value="16"<?php sel($udetailzoom == "15"); ?>>Full detail</option>
<option value="14"<?php sel($udetailzoom == "14"); ?>>Medium detail</option>
<option value="13"<?php sel($udetailzoom == "13"); ?>>Bare</option>
</select></td></tr>
<tr><th>Notes:</th>
<td><input type="text" name="notes" style="width: 98%;" title="Give a short name to your map. Include a nickname so you can search for your renders later." value="<?php echo(htmlspecialchars(preg_replace('/[\x00-\x1F\x7F]/', '', $unotes))); ?>" /></td></tr>
<tr><th>Code:</th>
<td><input type="text" name="code" style="width: 98%;" title="Enter the CAPTHCA validation code from the image below." autocomplete="off" /></td></tr>
</table>
<!-- br />
Your e-mail (optional):<br/>
<input type="text" name="email" /-->
<img src="gd.php" id="captcha" alt="Capcha, sorry, you need to write this text to the box below." title="Can't read? Start to render and you'll get a new code! Write this code to the box below." /><br/>
<input id="submit" name="render" type="submit" value="Start to render" title="This submits your selected area to a custom crafted OSM to PNG converter that will generate a printer friendly HTML output."/> |
<a id="permalink" href="<?php echo($map->getLink("")); ?>" title="Store the link from the URL bar for later. Remembers selection, but not the paper settings.">Permalink</a></p>
</form>

<!-- Job download panel -->
<div class="panel">
<h2>Download result</h2>
<p><a href="list.php" target="_blank">View all maps</a></p>
</div>

</div>
</div>
<script type="text/javascript">
// Values from PHP
var MAX_SQUARE_KM = <?php echo($map->MAX_SQUARE_KM); ?>;
var MAX_OBJ_PER_PAGE = <?php echo($map->MAX_OBJ_PER_PAGE); ?>;
var MAX_OBJ_PER_PAGE_MEDIUM = <?php echo($map->MAX_OBJ_PER_PAGE_MEDIUM); ?>;
var MAX_OBJ_PER_PAGE_BARE = <?php echo($map->MAX_OBJ_PER_PAGE_BARE); ?>;

$(document).ready(function () {

	initMap(<?php echo($map->CenterLat.",".$map->CenterLon.",".$map->Zoom);?>);

	// Selection box values from PHP
	var lat1 = <?php echo($map->SelectLat1 ? $map->SelectLat1 : "null") ; ?>;
	var lon1 = <?php echo($map->SelectLon1 ? $map->SelectLon1 : "null") ; ?>;
	var lat2 = <?php echo($map->SelectLat2 ? $map->SelectLat2 : "null") ; ?>;
	var lon2 = <?php echo($map->SelectLon2 ? $map->SelectLon2 : "null") ; ?>;

	if(lat1 && lon1 && lat2 && lon2) {
		reselect(lat1, lon1, lat2, lon2);
	}
});
</script>

<?php 
include 'footer.php'; 
?>
