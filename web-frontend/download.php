<?php
/*
 * render(myMap) - (c)2011-2018 Ferenc Veres
 * Licensed under GPL v3
 * 
 * Finds the render by job ID and redirects to it.
 * Used from the main page "Download result" section.
 */
if(array_key_exists("jobid", $_POST)
	&& preg_match("/^[a-zA-Z0-9]+$/", $_POST["jobid"]) == 1)
{
	$jobid = $_POST["jobid"];
	$isrunning = is_file("jobs/$jobid.render");

	if(is_dir("output/$jobid")) {
		header("Location: output/$jobid/$jobid.html"); 
	} else if($isrunning) {
		echo("Not found. Job not finished yet, please try again later.");
	} else {	
		echo("Not found. No such job.");
	}
}
else
{
	echo("Please fill jobID");
}
?>
