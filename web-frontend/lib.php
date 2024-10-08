<?php
/*
 * render(myMap) - (c)2011-2018 Ferenc Veres
 * Licensed under GPL v3
 * 
 * Routines and classes for the web frontend
 */

/**
 * Handles current map view information and operations
 * including current position, zoom level, paper settings
 */
class MapSettings {
	public $CenterLat = 47.51627321168; /*< Current view */
	public $CenterLon = 19.054412841797;
	public $Zoom = 17; /*< Current view's zoom */
	public $Css; /*< Selected style (dropdown) */
	public $Pages = "1"; /*< Selected number of pages ("WxH" or 1) */
	public $Paper = "a4p"; /*< Selected paper size */
	public $Notes = ""; /*< User entered title for the map */
	public $ServerUrl = 'http://tile.openstreetmap.org/';
	public $DetailZoom = 16; /*< Zoom level passed to MapCSS renderer, specifies detail level */
	public $SelectLat1 = null; /*< Box selection corners */
	public $SelectLon1 = null;
	public $SelectLat2 = null;
	public $SelectLon2 = null;

	// Constants
	public $R = 6378100; /*< Earth radius */
	public $DETAIL_MIN_ZOOM = 12; /*< Min zoom level from the detail dropdown */ 
	public $DETAIL_MAX_ZOOM = 17; /*< Min zoom level from the detail dropdown */ 
	public $PAGES_W_MAX = 3; /*< Maximum 3x3 pages for box */
	public $PAGES_H_MAX = 3; /*< Maximum 3x3 pages for box */
	public $BBOX_EDGE = 0.000; /*< Increase download area by this degree in all directions (not necessary since using OverPass) */
	public $MAX_SQUARE_KM = 18; /*< Maximum allowed rendered area */
	public $MAX_OBJ_PER_PAGE = 2000; /*< Maximum OSM nodes on a page */
	public $MAX_OBJ_PER_PAGE_MEDIUM = 2500; /*< Maximum OSM nodes in medium mode */
	public $MAX_OBJ_PER_PAGE_BARE = 3000; /*< Maximum OSM nodes in bare mode (excluding buildings) */
	public $SITEURL = "http://render.osmtippek.hu/";

	public $PAPERSIZES = array("a4p", "a4l", "letterp", "letterl");
	public $PAPERNAMES = array(
		"a4p" => "A4 portrait", 
		"a4l" => "A4 landsape", 
		"letterp" => "Letter portrait", 
		"letterl" => "Letter landsape");
	public $STYLES = array("shops", "housenumbers", "wheelchair");

	/**
	 * Clears actual position (but why?)
	 */
	private function clean() {
		$this->CenterLat = 0;
		$this->CenterLon = 0;
		$this->Zoom = 0;
	}

	/**
	 * Read from our own query string and set map properties
	 *
	 * returns true on success, false on fail
	 */
	public function readFromQuery()
	{
		global $_GET;
		$this->clean();

		// Restore coordinates from query
		if(array_key_exists('lat', $_GET)) {
			$this->CenterLat = round(floatval($_GET['lat']), 5);
		}
		if(array_key_exists('lon', $_GET)) {
			$this->CenterLon = round(floatval($_GET['lon']), 5);
		}
		if(array_key_exists('zoom', $_GET)) {
			$this->Zoom = intval($_GET['zoom']);
		}

		// Restore selection from query
		// Box selection in form post? (stronger than query)
		$this->getClientSelection();

		if($this->SelectLat1 === null && array_key_exists('box', $_GET)) {
			$sel = explode(',', $_GET['box']);
			
			// Box selection in query
			if(count($sel) == 4) {
				$this->SelectLat1 = round(floatval($sel[0]), 5);
				$this->SelectLon1 = round(floatval($sel[1]), 5);
				$this->SelectLat2 = round(floatval($sel[2]), 5);
				$this->SelectLon2 = round(floatval($sel[3]), 5);
			}
		}

		// Store paper settings from query string
		$this->Pages = "1";
		if(array_key_exists('pages', $_GET)) {
			list($w, $h) = $this->getPages($_GET['pages']);
			if($w > 1 || $h > 1) {
				$this->Pages = $w."x".$h;
			}
		}
		$this->Paper = "a4p";
		if(array_key_exists('paper', $_GET) && in_array($_GET['paper'], $this->PAPERSIZES)) {
			$this->Paper = $_GET['paper'];
		}
		$this->Css = "shops";
		if(array_key_exists('style', $_GET) && in_array($_GET['style'], $this->STYLES)) {
			$this->Css = $_GET['style'];
		}
		$this->DetailZoom = "16";
		if(array_key_exists('detail', $_GET) && in_array($_GET['detail'], array(13, 14, 16))) {
			$this->DetailZoom = intval($_GET['detail']);
		}

		return ($this->CenterLat != 0 && $this->CenterLon != 0 && $this->Zoom != 0);
	} 

	/**
	 * Get lat/lon/zoom from OpenStreetMap.org permalink and set map coordinates
	 *
	 * returns true on success, false on fail
	 */
	public function readFromPermaLink($osmlink) 
	{
		$this->clean();
		$match = preg_match('/^.*#map=([0-9.\/]+).*$/', $osmlink, $matches);
		if($match !== false) {
			$q = explode('/', $matches[1]);

			if(count($q) == 3) {
				$lat = floatval($q[1]);
				$lon = floatval($q[2]);
				$zoom = intval($q[0]);

				if($lat != 0 && $lon != 0 && $zoom != 0) {
					$this->CenterLat = $lat;
					$this->CenterLon = $lon;
					$this->Zoom = $zoom;
					return true;
				}
			}
		}
		return false;
	}

	/**
	 * Calcualtes the distance in meters - Mercator projection - between two latitutde values
	 */
	public function latDistance($lat1, $lat2) {
		$rad1 = $lat1*(pi()/180);
		$rad2 = $lat2*(pi()/180);
		$y1 = log( (1 + sin($rad1)) / cos($rad1) ) * $this->R;
		$y2 = log( (1 + sin($rad2)) / cos($rad2) ) * $this->R;
		return round(abs($y1 - $y2));
	}

	/**
	 * Calcualtes the distance in meters - Mercator projection - between two longitude values
	 */
	public function lonDistance($lon1, $lon2) {
		$rad1 = $lon1*(pi()/180);
		$rad2 = $lon2*(pi()/180);
		return round(abs($rad1 - $rad2) * $this->R);
	}

	/**
	 * Makest Lat1 and Lon1 smaller number than Lat2 and Lon2 by exhcanging values if necessary 
	 */
	public function normalizeSelection() {
		if($this->SelectLat1 > $this->SelectLat2) {
			$a = $this->SelectLat1;
			$this->SelectLat1 = $this->SelectLat2;
			$this->SelectLat2 = $a;
		}
		if($this->SelectLon1 > $this->SelectLon2) {
			$a = $this->SelectLon1;
			$this->SelectLon1 = $this->SelectLon2;
			$this->SelectLon2 = $a;
		}
	}

	/**
	 * Gets a link for navigation or selection
	 *
	 * @param $mode What type of link to retun ("osm" to jump to osm, "action" for form action, empty for permalink)
	 */
	public function getLink($mode)
	{
		$linklat = $this->CenterLat;
		$linklon = $this->CenterLon;
		$zoom = $this->Zoom;

		// Go to openstreetmap.org
		// FIXME: this is now unused, becasue it's created on client side. Remove?
		if($mode == "osm") {
			return("http://www.openstreetmap.org/#map=$zoom/$linklat/$linklon");
		}

		// Map position
		$link = "index.php?lat=$linklat&lon=$linklon&zoom=".$zoom;

		// Selection box
		if($this->SelectLat1) {
			$link .= "&box=".$this->SelectLat1.","
				.$this->SelectLon1.","
				.$this->SelectLat2.","
				.$this->SelectLon2;
		}

		// Form fields (dropdowns)
		if($mode != "action") {
			$link .= "&pages=".$this->Pages;
			$link .= "&paper=".$this->Paper;
			$link .= "&style=".$this->Css;
			$link .= "&detail=".$this->DetailZoom;
		}
		return $link;
	}

	/**
	 * Clear selection box FIXME: needed? Was for tiles, but updated.
	 */
	public function clearSelection() {
		$this->SelectLat1 = null;
		$this->SelectLon1 = null;
		$this->SelectLat2 = null;
		$this->SelectLon2 = null;
		$this->SelectZoom = 15;
	}

	/**
	 * Returns the maximum possible zoom level for the current map
	 */
	public function getMaxZoom() {
		// Could depend on tile server, but currently harcoded
		return 18;
	}
	/**
	 * Returns the minimum possible zoom level for the current map
	 */
	public function getMinZoom() {
		// Let's not allow 1 tile and 2x2 tiles, too small
		return 2;
	}

	/**
	 * Checks the form post values before calling submitRender() and stores form fields in member variables.
	 *
	 * Most of these are unlikely to be invalid since they are dropdowns. So this is just safety check.
	 *
	 * returns true on form OK, false on not OK and echo prints the error.
	 */
	public function checkForm() {
		global $_POST;

		$form_error = "";

		// MapCSS selection
		$this->Css = "shops";
		if(array_key_exists("style", $_POST) && in_array($_POST["style"], $this->STYLES)) {
			$this->Css = $_POST["style"];
		} else {
			$form_error .= "No style selected.";
		}
		// Readable title for the drawing
		$this->Notes = "";
		if(array_key_exists("notes", $_POST)) {
			$this->Notes = preg_replace('/[\x00-\x1F\x7F]/', '', $_POST["notes"]); // Removes some CTRL chars
			if(strlen($this->Notes) > 100) {
				$this->Notes = substr($this->Notes, 0, 100);
			}
		}
		// Paper selection
		$this->Paper = "a4p";
		if(array_key_exists("paper", $_POST) && in_array($_POST["paper"], $this->PAPERSIZES)) {
			$this->Paper = $_POST["paper"];
		} else {
			$form_error .= "No paper selected.";
		}
		// Detail zoom level (passed to CeyX for applying MapCSS rules)
		$this->DetailZoom = 15;
		if(array_key_exists("detailzoom", $_POST) && ($this->DetailZoom = intval($_POST["detailzoom"])) > 0
			&& $this->DetailZoom >= $this->DETAIL_MIN_ZOOM && $this->DetailZoom <= $this->DETAIL_MAX_ZOOM) {
			// (detailzoom set in conditions list!)
		} else {
			$form_error .= "No detail zoom level selected.";
		}
		if(array_key_exists('pages', $_POST)) {
			list($w, $h) = $this->getPages($_POST['pages']); // Also checks allowed limit, returns 1,1 minimum!
		} else {
			$w = 1;
			$h = 1;
		}
		if($w == 1 && $h == 1) {
			$this->Pages = "1";
		} else {
			$this->Pages = $w."x".$h;
		}

		// Exit on form data input error
		if($form_error) {
			echo $form_error;
			return false;
		}
		return true;
	}

	/**
	 * Passes the selection to the renderer via creating text data file
	 *
	 * returns Job ID (string) on success, false on failure (no selection, file error)
	 */
	function submitRender()
	{
		$lat1 = 0;
		$lon1 = 0;
		$lat2 = 0;
		$lon2 = 0;
		list($w, $h) = ($this->Pages == '1' ? array(1,1) : explode('x', $this->Pages));

		// Don't we have box selection? (initalized from index.php)
		if($this->SelectLat1 !== null) {

			$this->normalizeSelection();

			list($lat1, $lon1, $lat2, $lon2) = Array($this->SelectLat1, $this->SelectLon1, $this->SelectLat2, $this->SelectLon2);

			if($w == 1 && $h == 1) {
				$mode = "onebox";
			} else {
				$mode = "boxes";
				// Divide for pages
				// FIME: No round or round to 5, because this error adds up in --batch
				$box_lat2 = round($lat1 + (($lat2 - $lat1) / $h), 5);
				$box_lon2 = round($lon1 + (($lon2 - $lon1) / $w), 5);
			}
		} else {
			echo("No selection!\n");
			return false;
		}

		// Round coordinates
		$lat1 = round($lat1, 5);
		$lon1 = round($lon1, 5);
		$lat2 = round($lat2, 5);
		$lon2 = round($lon2, 5);

		// http://nominatim.openstreetmap.org/reverse?format=json&lat=40.4332&lon=-3.70591&zoom=12

		// Outside usable merkator values?
		if(abs($lat1) > 80 || abs($lat2) > 80) {
			echo("Cannot render near to poles. Go within -80 and 80 please!\n");
			return false;
		}

		// Full download size in meters
		$dLat = $this->latDistance($lat1, $lat2);
		$dLon = $this->lonDistance($lon1, $lon2);
		$square_km = round(($dLat/1000) * ($dLon/1000),1);
		if($square_km > $this->MAX_SQUARE_KM) {
			echo("Area too big (${dLon}m x ${dLat}m = ".$square_km."km<sup>2</sup>) (Max: $this->MAX_SQUARE_KM square kilometers)!\n");
			return false;
		}

		// Make random job ID
		do {
			$name = $this->makeRandomName();
		} while(file_exists("jobs/$name.$mode.render"));
		
		// Output job data file
		$out = fopen("jobs/$name.$mode.render", "w");

		if($out === false) {
			echo("File open failed for jobs/$name.$mode.render\n");
			return false;
		}
		$sep = " "; // Field separator in txt file

		fwrite($out, $name.$sep);
		fwrite($out, $mode.$sep);

		if($mode == 'onebox') {
			fwrite($out, intval($this->DetailZoom).$sep);
			fwrite($out, $lat1.$sep);
			fwrite($out, $lon1.$sep);
			fwrite($out, $lat2.$sep);
			fwrite($out, $lon2.$sep);
			fwrite($out, $this->Css.$sep);
			$this->generateHtml($mode, $name, $this->DetailZoom, 0, 0, $this->Notes, $this->Paper, $dLon, $dLat);
		} else if($mode == 'boxes') {
			fwrite($out, intval($this->DetailZoom).$sep);
			fwrite($out, $lat1.$sep);
			fwrite($out, $lon1.$sep);
			fwrite($out, $box_lat2.$sep);
			fwrite($out, $box_lon2.$sep);
			fwrite($out, $w.$sep);
			fwrite($out, $h.$sep);
			fwrite($out, $this->Css.$sep);
			$this->generateHtml($mode, $name, $this->DetailZoom, $w, $h, $this->Notes, $this->Paper, round($dLon/$w), round($dLat/$h));
		}

		// bbox increased a little for download (about 200m at Budapest)
		fwrite($out, ($lat1 - $this->BBOX_EDGE).$sep); // bottom
		fwrite($out, ($lon1 - $this->BBOX_EDGE).$sep); // left
		fwrite($out, ($lat2 + $this->BBOX_EDGE).$sep); // top
		fwrite($out, ($lon2 + $this->BBOX_EDGE)); // right
		fwrite($out, "\n");

		fclose($out);

		// FIXME: protection for "jobflood"!
		return $name;
	}

	/**
	 * Generates a random job ID - does not check older job existance
	 */
	private function makeRandomName() {
		$chrs = "123456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ";

		$name = "";
		$namelen = rand(5,10);
		for($i = 0; $i < $namelen; $i++) {
			$name .= substr($chrs, rand(0,strlen($chrs)-1), 1);
		}
		return $name;
	}

	/** 
	 * Read client side JS selection from form post (hidden fields), sets $this-SelectLat1, Lon1, Lat2, Lon2 (to null if no data found)
	 *
	 */
	public function getClientSelection() {
		global $_POST;
		if(array_key_exists('selectlat1', $_POST)
			&& array_key_exists('selectlon1', $_POST)
			&& array_key_exists('selectlat2', $_POST)
			&& array_key_exists('selectlon2', $_POST))
		{
			$lat1 = floatval($_POST['selectlat1']);
			$lon1 = floatval($_POST['selectlon1']);
			$lat2 = floatval($_POST['selectlat2']);
			$lon2 = floatval($_POST['selectlon2']);

			if($lat1 < $lat2 && $lon1 < $lon2
				&& $lat1 >= -90 && $lat1 <= 90
				&& $lat2 >= -90 && $lat2 <= 90
				&& $lon1 >= -180 && $lon1 <= 180
				&& $lon2 >= -180 && $lon2 <= 180) {

					$this->SelectLat1 = $lat1;
					$this->SelectLon1 = $lon1;
					$this->SelectLat2 = $lat2;
					$this->SelectLon2 = $lon2;
					return;
			}
		}
		$this->SelectLat1 = null;
		$this->SelectLon1 = null;
		$this->SelectLat2 = null;
		$this->SelectLon2 = null;
	}

	/**
	 * Reads page selection from the passed string (form value)
	 *
	 * @returns Array of two values, number of pages in X and Y direction. 1x1 if PAGES_*_MAX exceeded.
	 */
	public function getPages($pagesval) {

		// Format is "2x3"
		$parts = explode('x', $pagesval);
		if(count($parts) == 2) {
			$w = intval($parts[0]);
			$h = intval($parts[1]);

			if($w > 0 && $w <= $this->PAGES_W_MAX && $h > 0 && $h <= $this->PAGES_H_MAX) {
				return array($w, $h);
			}
		}
		return array(1,1);
	}

	/**
	 * Generates a HTML for the generated images
	 */
	public function generateHtml($mode, $name, $zoom, $w, $h, $notes, $paper, $meterx, $metery) {

		$template = file_get_contents("map_template.html");
		$copyright = "<br/>Original map data &copy; OpenSteetMap and contributors ODbL";
		$date = date("D Y-m-d");
		$pages = $w * $h;

		// This map in HTML is added as "{map}" to map_template.html
		$html = "";

		if($mode == "onebox") {
			$html .= "<div class=\"printlabel\">render(myMap) - Job ID: $name - Page 1 of 1 - $date  - <strong>".htmlspecialchars($notes)."</strong><br />"
				.$this->SITEURL.$this->getLink("")
				."$copyright</div>";
			$img = "map$zoom.png";
			$html .= "<div class=\"tile\"><a href=\"$img\"><img src=\"$img\"></a></div>\n";
		} else if($mode == "boxes") {
			// Go rows and columns to add tiles
			$p = 1;
			for($y = $h - 1; $y >= 0; $y--) { // Something is rotated here, maybe CEYX (same in createMiniOverview)
				$html .= "<div class=\"row\">\n";

				for($x = 0; $x < $w; $x++) {
					$html .= createMiniOverview($w, $h, $x, $y);
					// Title for each box
					$html .= "<div class=\"printlabel\">render(myMap) - Job ID: $name - Slice $x,$y - Page $p of $pages - $date - <strong>".htmlspecialchars($notes)."</strong><br />"
						.$this->SITEURL.$this->getLink("")
						."$copyright</div>";
					$img = "$zoom/$x/$y.png";
					$html .= "<div class=\"tile\"><a href=\"$img\"><img src=\"$img\"></a></div>\n";
					$p++;
				}
				$html .= "</div>\n";
			}
		}

		$f = fopen("jobs/$name.html", "w");

		if($f === false) {
			echo("File create failed for jobs/$name.html\n");
			return false;
		}
		
		$template = str_replace("{url}", $this->SITEURL.$this->getLink(""), $template);
		$template = str_replace("{date}", $date, $template);
		$template = str_replace("{jobid}", $name, $template);
		$template = str_replace("{pages}", $pages, $template);
		$template = str_replace("{notes}", htmlspecialchars($notes), $template);
		$template = str_replace("{paper}", $paper, $template);
		$template = str_replace("{printon}", $this->PAPERNAMES[$paper], $template);
		$template = str_replace("{meterx}", $meterx, $template);
		$template = str_replace("{metery}", $metery, $template);
		$template = str_replace("{map}", $html, $template, $template);
		fwrite($f, $template);

		fclose($f);
	}
}

/**
 * Outputs a small grid table for every page, highlighting current page's box
 */
function createMiniOverview($w, $h, $x, $y) {
	$res = "\n<table class=\"overview\">";
	for($row = $h - 1 ; $row >= 0; $row--) { // Upside down, like the HTML generating see above
		$res .= "<tr>";
		for($col = 0; $col < $w; $col++) {
			$res .= "<td>".($col == $x && $row == $y ? "X" : "")."</td>";
		}
		$res .= "</tr>";
	}
	$res .= "</table>\n";
	return $res;
}

/* Global functions */
function sel($select) {
	if($select) { echo(" selected=\"selected\""); }
}
?>
