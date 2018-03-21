#!/bin/bash

# THIS DOES NOT WORK!!!!! JUST TEST!!!!!!

. /home/render/bin/rendermymap.config

# Cannot get these rexeps work in egrep and sed below
# Exampmple input:
# GOIkz0 onebox 14 47.5183 19.0532 47.5164 19.0558 shops 47.5213 19.0502 47.5134 19.0588

MODEMASK="\(onetile|tiles|onebox|boxes\)"
NAMEMASK="[a-zA-Z0-9]\{1,25\}"
# Read FIFO forever
while [ 1 == 1 ]
do
	JOBS=`cat $FIFOFILE`
	echo $MODEMASK
	for JOB in "$JOBS"
	do
		echo $JOB | egrep -q  "/^$NAMEMASK $MODEMASK /"
		if [ "$?" == "0" ] 
		then
			FNAME=`echo $JOB | sed "s/^($NAMEMASK) $MODEMASK.*$/$1$2.render/"`
			echo $JOB $JOBDIR/$FNAME
		else 
			echo Wrong job on FIFO: $JOB
		fi
	done
done
