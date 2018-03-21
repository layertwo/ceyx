<?php
/*
 * render(myMap) - (c)2011-2018 Ferenc Veres
 * Licensed under GPL v3
 * 
 * This web service checks if job is ready
 * returns { "job" : "STATUS" } see below for STATUS values
 */
header("Expires: Mon, 26 Jul 1997 05:00:00 GMT");
header("Cache-Control: no-cache");
header("Pragma: no-cache");
header("Content-type: application/json; charset=UTF-8");
$status = "nostatus";
if(array_key_exists('id', $_GET)) {
	$job = $_GET['id'];
	if(!preg_match('/^[a-zA-Z0-9]{1,25}$/', $job)) {
		$status = "badrequest";
	} else if(is_file("output/$job.txt")) {
		$status = "fail";
	} else if(!is_dir("output/$job")) {
		// No dir yet
		$status = "waiting";
	} else if(!is_file("output/$job/$job.html")) {
		// Dir exists but no HTML file yet
		$status = "working";
	} else {
		$status = "ready";
	}
} else {
	$status = "badrequest";
}
echo '{ "job" : "'.$status.'" }';
?>
