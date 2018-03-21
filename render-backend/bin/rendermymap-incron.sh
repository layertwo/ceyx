#!/bin/bash
# Passes the new rendering job file to the renderer
# Should be called from incron

# Incron example (watchdir, watchtype, startwhat, path+file as param)
#/home/render/web/rendermymap/jobs IN_CLOSE_WRITE /home/render/bin/rendermymap-incron.sh $@/$#

cd /home/render/bin/
. rendermymap.config
./rendermymap.sh $* >>$LOGFILE 2>&1
