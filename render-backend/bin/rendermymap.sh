#!/bin/bash

# Gets rendering jobs from the website, downloads from OSM API and renders with CeyX
# Call with rendermymap-findjobs.sh or rendermymap-incron.sh

. /home/render/bin/rendermymap.config

APIURL=https://lz4.overpass-api.de/api/interpreter
JOB=$1
DIR=`dirname $1`
FILE=`basename $1`
OSMFILE=$DATADIR/${FILE%%.*}.osm
HTMLFILE=$DIR/${FILE%%.*}.html
DLDIR=$OUTDIR/${FILE%%.*}
OUTHTMLFILE=$DLDIR/${FILE%%.*}.html
ERRORFILE=$OUTDIR/${FILE%%.*}.txt

# Number of pixels to render on a page
PAGEPX=2007  # 17cm on 300 DPI
#PAGEPX=4014  # 17cm on 600 DPI

# Regexps for data file parsing
# optional minus, max 3 number, optional dot plus max 4 number
DEGMASK="-?[0-9]{1,3}(\\.[0-9]{1,5})?"
CSSMASK="(shops|housenumbers|wheelchair)"
MODEMASK="(onebox|boxes)"
NAMEMASK="[a-zA-Z0-9]{1,25}"
ZOOMMASK="(10|11|12|13|14|15|16|17|18|19)"
TILEMASK="[0-9]{1,6}"

function errorexit {
	echo $1
	echo $1 >$ERRORFILE
	exit 1
}

# JOB file basic checks
if [ "${JOB##*.}" != "render" ]
then
	# Ignoring this error
	echo "Error: not a .render file $JOB"
	exit 1
fi

if [ ! -d $DATADIR ]
then
	mkdir -p $DATADIR
fi

# Download OSM Data (parameter is bbox string)
function downloadosm {
	if [ "$2" = "13" ]
	then
		# Bare format's zoom value, filter out some OSM data
		QUERY="$APIURL?data=[out:xml][timeout:25];(nwr($1);-(node[amenity]($1);node[shop]($1);way[building]($1);>;););out meta;>;out meta qt;"
	else
		# Medium or full detail, download complete OSM
		QUERY="$APIURL?data=[out:xml][timeout:25];(node($1);way($1);relation($1););out meta;>;out meta qt;"
	fi

	echo wget "$QUERY" -O "$OSMFILE"
	wget "$QUERY" -O "$OSMFILE" 2>&1
	if [ "$?" != "0" ] 
	then
		errorexit "Error: wget returned error code $?"
	fi
}

# Check if JOB data file matches specific format ($1). Exit if not.
function checkdata {
	egrep -q "$1" "$JOB"
	if [ "$?" != "0" ] 
	then
		errorexit "Error: Passed file does not match required format $FILE"
	fi
}

# Process job
if [ -f "$JOB" ]
then
	echo "---- $JOB -----"
	cat "$JOB"
	cd "$CEYXDIR"

	case "$FILE" in
		*.onebox.render)
			# Render a single box 
			# Data format check: zoom rlat1 rlon1 rlat2 rlon2 css lat1 lon1 lat2 lon2
			checkdata "^$NAMEMASK $MODEMASK $ZOOMMASK $DEGMASK $DEGMASK $DEGMASK $DEGMASK $CSSMASK $DEGMASK $DEGMASK $DEGMASK $DEGMASK$"
			read NAME MODE ZOOM RAT1 RON1 RAT2 RON2 CSS LAT1 LON1 LAT2 LON2 <$JOB
			rm -f "$JOB"

			# FIXME: check area somehow? 
			downloadosm "$LAT1,$LON1,$LAT2,$LON2" "$ZOOM"
			mkdir "$DLDIR"

			echo ./osm2png.py -s ${PAGEPX} -a -z $ZOOM -b $RAT1,$RON1,$RAT2,$RON2 -r "$CSS.mapcss" -d "$OSMFILE" -o "$DLDIR/map$ZOOM.png"
			./osm2png.py -s ${PAGEPX} -a -z $ZOOM -b $RAT1,$RON1,$RAT2,$RON2 -r "$CSS.mapcss" -d "$OSMFILE" -o "$DLDIR/map$ZOOM.png" 2>&1
		;;
		*.boxes.render)
			# Render a box in batch splits
			# Data format check: zoom rlat1 rlon1 rlat2 rlon2 width height css lat1 lon1 lat2 lon2
			checkdata "^$NAMEMASK $MODEMASK $ZOOMMASK $DEGMASK $DEGMASK $DEGMASK $DEGMASK [1-9] [1-9] $CSSMASK $DEGMASK $DEGMASK $DEGMASK $DEGMASK$"

			read NAME MODE ZOOM RAT1 RON1 RAT2 RON2 W H CSS LAT1 LON1 LAT2 LON2 <$JOB
			rm -f "$JOB"

			# FIXME: check area somehow? 
			downloadosm "$LAT1,$LON1,$LAT2,$LON2" "$ZOOM"
			mkdir "$DLDIR"

			echo ./osm2png.py -s ${PAGEPX} -a -z $ZOOM -b $RAT1,$RON1,$RAT2,$RON2 --batch=$W,$H -r "$CSS.mapcss" -d "$OSMFILE" -o "$DLDIR"
			./osm2png.py -s ${PAGEPX} -a -z $ZOOM -b $RAT1,$RON1,$RAT2,$RON2 --batch=$W,$H -r "$CSS.mapcss" -d "$OSMFILE" -o "$DLDIR" 2>&1
		;;
	esac
		
	# HTML file exists for batch jobs
	if [ -f "$HTMLFILE" ] 
	then
		echo cp "$HTMLFILE" "$OUTHTMLFILE"
		cp "$HTMLFILE" "$OUTHTMLFILE"
		rm -f "$HTMLFILE"
	fi

	# Delete temp files
	rm -f "$OSMFILE"
	echo "---------- OK $OSMFILE --------"
else
	echo "Passed file does not exist: $JOB"
fi

