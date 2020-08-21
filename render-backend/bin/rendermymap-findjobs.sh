#!/bin/bash
# render(myMap) - rendermymap-findjobs.sh
# Finds new rendering jobs and calls the renderer
# It should be run from normal cron or manually for testing purposes
# An alternative to rendermymap-incron.sh

. /home/render/bin/rendermymap.config

find $JOBDIR -name \*.render -exec echo {} \;
find $JOBDIR -name \*.render -exec rendermymap.sh {} \; >>$LOGFILE 2>&1
