<?php
/* 
 * render(myMap) - (c)2011-2018 Ferenc Veres
 * Licensed under GPL v3
 * 
 * This code lists all renders, allows to search in them.
 * 
 * Information is parsed directly from the 
 * created HTML files (e.g. title).
 */
session_start();
include 'header.php';
?>
<div id="projectlist">

<p><a href="index.php">Back to the map</a></p>
<h1>Browse <a href="list.php">all</a> renders</h1>
<?php

$dir = "output";
$start = 0;
$itemsperpage = 15;
$itemsperrow = 3;
$page = 0;

// Check if we need a specific page
if(array_key_exists("page", $_GET)) {
	$page = intval($_GET["page"]);
}

// Load list of all rendered maps
$jobs = loadjobs($dir);

// Filter renders by search
if(count($jobs) > 0) {

	showSearchForm();
	$q = "";
	if(array_key_exists("q", $_GET) && $_GET["q"]) {
		$q = $_GET["q"];
		$jobs = doSearch($jobs, $q);
	}
}

// Show results of the current page and current search if any
if(count($jobs) > 0) {

	$startitem = $page * $itemsperpage;
	$numitems = count($jobs);
	$i = 0;
	$inrow = 0;
	showPager($page, $startitem, $numitems, $itemsperpage, $q);
	foreach($jobs as $date => $file) {
		// Skip until start item
		if($i >= $startitem) {

			if($inrow == 0) {
				echo("<div class=\"projectrow\">\n");
			}

			processProject($jobs[$date], $date, $numitems - $i);

			$inrow++;
			if($inrow >= $itemsperrow) {
				echo("</div>\n");
				$inrow = 0;
			}
			// Exit if items per page
			if($i >= $startitem + $itemsperpage - 1) {
				if($inrow != 0) {
					echo("</div>\n");
				}
				break;
			}
		}
		$i++;
	}
	if($i == $numitems) {
		echo("</div>\n");
	}
	showPager($page, $startitem, $numitems, $itemsperpage, $q);
} else {
	echo("<p><strong>There is nothing.</strong></p>");
}

/**
 * Displays prev-next pager
 */
function showPager($page, $startitem, $numitems, $itemsperpage, $q) {
	echo("<div class=\"pager\">");
	$sep = "";
	$search = "";
	if($q) {
		$search = "&q=".htmlspecialchars($q);
	}
	if($page > 0) {
		echo("<a href=\"list.php\">&lt;&lt; First</a> | ");
		$p = ($page != 1 ? "?page=" . ($page - 1) : "");
		if(!$p) {
			$p = str_replace("&", "?", $search);
		} else {
			$p .= $search;
		}
		echo("<a href=\"list.php".$p. "\">&lt; Previous</a> |");
	} else {
		echo("First | Previous | ");
	}
	if($startitem + $itemsperpage < $numitems) {
		echo("<a href=\"list.php?page=" . ($page + 1) .$search. "\">Next &gt;</a> | ");
		echo("<a href=\"list.php?page=" . intval($numitems / $itemsperpage) .$search. "\">Last &gt;&gt;</a>");
	} else {
		echo("Next | Last");
	}
	echo("</div>");
}

/**
 * Displays search form
 */
function showSearchForm() {
	$usearch = (array_key_exists("q", $_GET) ? $_GET["q"] : "");
	?>
	<form action="list.php" method="get" id="projectsearch">
		<input type="text" size="30" maxlength="128" name="q" value="<?php echo(htmlspecialchars($usearch)) ?>" title="Search in notes, job ID and dates."/>
		<input type="submit" name="search" value="Search" />
	</form>
	<?php
}
/**
 * Filters those JOBS that match Q search, returns a new filtered list of job IDs.
 */
function doSearch($jobs, $q) {

	global $dir;

	$lq = strtolower($q);
	$res = array();
	foreach($jobs as $date => $file) {
		// Check match in job ID or date
		if(strpos($file, $q) !== false || strpos(date("D Y-m-d", $date), $q) !== false) {
			$res[$date] = $file;
		} else {
			$title = readTitle("$dir/$file/$file.html");
			if(strpos(strtolower($title), $lq) !== false) {
				$res[$date] = $file;
			}
		}
	}
	return $res;
}

/**
 * Loads all JOB IDs into an array, ordered by date desc
 *
 * @returns Array Key is date timestamp, value is JOB ID (dir name)
 */
function loadjobs($dir) {
	$jobs = array();
	if (is_dir($dir)) {
		if ($dh = opendir($dir)) {
			while (($file = readdir($dh)) !== false) {
				if($file == "." || $file == ".." || !is_dir($dir."/".$file)) { continue; }

				$jobs[filemtime($dir."/".$file)] = $file;
			}
			closedir($dh);
		}
	}
	krsort($jobs);
	return $jobs;
}

/**
 * Show one render on the list
 * 
 * Reads title from the output HTML file.
 * Generates preview image if missing.
 */
function processProject($jobid, $date, $counter) {
	global $dir;
	$jobdir = $dir."/".$jobid;

	$title = readTitle($jobdir."/".$jobid.".html");

	// Create resized PNG if needed
	if(!is_file("previews/$jobid.png")) {
		createPreview($jobid);
	}
	if(is_file("previews/$jobid.png")) {
		$preview = "previews/$jobid.png";
	} else {
		$preview = "images/render_progress2.gif"; // image made from output
	}
	// Output project as HTML
?>
	<div class="project<?php  ?>">
		<div class="preview">
			<a href="output/<?php echo("$jobid/$jobid.html"); ?>"><img src="<?php echo($preview); ?>" /></a>
		</div>
		<h2><?php echo($counter) ?>. <a href="output/<?php echo("$jobid/$jobid.html"); ?>"><?php echo($title); ?></a></h2>
		<p><?php echo(date("D Y-m-d", $date)." "); ?><br/><em><?php echo($jobid) ?></em></p>
	</div>
<?php
}

/**
 * Reads the <title> section from HTML file. Returns "No title" if not found.
 */
function readTitle($htmlfile) {
	$title = "";
	// Read project title from output HTML file
	if(is_file($htmlfile)) {
		$html = file_get_contents($htmlfile);
		$html = str_replace(array("\n", "\r"), '', $html);
		if(preg_match("/.*<title>[^<]+<\/title>.*/", $html)) {
			$title = preg_replace("/.*<title>([^<]+)<\/title>.*/", "$1", $html);
			$title = str_replace("render(myMap) - ", "", $title);
		}
	}

	if(!trim($title)) {
		$title = "No title";
	}
	return $title;
}

/**
 * Creates a small computed image from the big rendered map images
 */
function createPreview($jobid) {
	global $dir;
	$jobdir = $dir."/".$jobid;

	// Find rendered images of the project
	$pics = array(); // array of arrays for X / Y image matrix
	if ($dh = opendir($jobdir)) {
		while (($file = readdir($dh)) !== false) {
			if($file == "." || $file == "..") { continue; }

			// "onebox" has map17.png (zoom level)
			if(is_file($jobdir."/".$file) 
				&& preg_match("/^map[\d]+.png$/", $file)) {

				$pics[0] = array("$jobdir/$file");
				break;

			// "boxes" has 17/0/0.png (zoom level)
			} else if(is_dir($jobdir."/".$file) 
				&& preg_match("/^[\d]+$/", $file) 
				&& is_file("$jobdir/$file/0/0.png")) {

				$pics = findRenderedImages("$jobdir/$file", true);
			}
		}
		closedir($dh);
	}
	if(count($pics) > 0) {

		// $pics array is two dimensional, first index choises an X coordinate, second is an Y
		$xcount = count($pics);
		$ycount = count($pics[0]);

		// Small-size image: resize with keep aspect ratio
		$width = 300;
		$height = 300;
		list($width_orig, $height_orig) = getimagesize($pics[0][0]); // All original images should be the same

		// Ratio calc needs total original images estate
		$ratio_orig = ($width_orig * $xcount) / ($height_orig * $ycount);
		if ($width/$height > $ratio_orig) {
		   $width = floor($height*$ratio_orig);
		} else {
		   $height = floor($width/$ratio_orig);
		}

		$smallwidth = floor($width / $xcount);
		$smallheight = floor($height / $ycount);


		// Output image - a mosaic 
		$image_p = imagecreatetruecolor($smallwidth * $xcount, $smallheight * $ycount);

		for($y = 0; $y < $ycount; $y++) {
			for($x = 0; $x < $xcount; $x++) {
				//echo("Adding ".$pics[$x][$y]." to ".($x * $smallwidth).",".($y * $smallheight)."<br>");
				// Add each output image to the mosaic
				$image = imagecreatefrompng($pics[$x][$y]);
				imagecopyresampled($image_p, $image, 
					$x * $smallwidth, $y * $smallheight,
					0, 0, $smallwidth, $smallheight, $width_orig, $height_orig);
				imagedestroy($image);
			}
		}

		// Save preview image
		imagepng($image_p, "previews/$jobid.png", 9);
		imagedestroy($image_p);
	}

}

/**
 * In Ceyx output dir finds the images
 * 
 * @dir is the "zoom"s dir, e.g. "output/DfgA325fd/15". Under that each number is an X, under that each file is an Y.
 * @reverse Sorts the "Y" png files in reverse order (recently CeyX makes that, but I forgot why, so parameter for later improvement)
 */
function findRenderedImages($dir, $reverse) {

	$pics = array();
	$xdirs = array();

	// Find dirs, that represent "x" coordinate
	if ($dh = opendir($dir)) {
		
		while (($xdir = readdir($dh)) !== false) {
			if(is_dir("$dir/$xdir") && preg_match("/^\d+$/", $xdir)) {
				array_push($xdirs, $xdir);
			}
		}
		closedir($dh);

		// No match (unlikely..)
		if(count($xdirs) == 0) {
			return null;
		}
		sort($xdirs); // Sort dirs so they go left to right

		// Loop each "x dir" and find the y.png files in it
		foreach($xdirs as $xdir) {
			if ($dh = opendir("$dir/$xdir")) {
				while (($yfile = readdir($dh)) !== false) {
					if(is_file("$dir/$xdir/$yfile") && preg_match("/^\d+.png$/", $yfile)) {
						if(!array_key_exists($xdir, $pics)) {
							$pics[$xdir] = array();
						}
						array_push($pics[$xdir], "$dir/$xdir/$yfile");
					}
				}
			}
		}
		closedir($dh);

		// Need 2, 1, 0 order, as CeyX (currently?, but not for older renders!) counts bottom to top
		for($x = 0; $x < count($pics); $x++) {
			if($reverse) {
				rsort($pics[$x]);
			} else {
				sort($pics[$x]);
			}
		}
		return $pics;
	}
}
include 'footer.php'; 
?>
