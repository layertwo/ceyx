#!/bin/bash
# Passes the new rendering job file to the renderer
# Should be called from incron

# Incron example (watchdir, watchtype, startwhat, path+file as param)
#/home/render/web/rendermymap/jobs IN_CLOSE_WRITE /home/render/bin/rendermymap-incron.sh $@/$#

cd /home/render/bin/
lockfile -r 75 -l 600 .rendering-lock || exit
. rendermymap.config
ulimit -Sv1310720
nice -n 20 ./rendermymap.sh $* >>$LOGFILE 2>&1
rm -f .rendering-lock
