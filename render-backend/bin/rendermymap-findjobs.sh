#!/bin/bash
# Find new rendering jobs and calls the renderer, it should be run from normal cron
# And alternative to rendermymap-incron.sh

. /home/render/bin/rendermymap.config

find $JOBDIR -name \*.render -exec /home/render/bin/rendermymap.sh {} \; >>$LOGFILE 2>&1
