#!/bin/bash

OIFS="$IFS"
IFS=$'\n'
LOGFILE='restart.txt'

runscript(){
  sudo mount -a
  python3 pyKraken_Lattice_New.py
}

writelog() {
  now=`date`
  echo "$now $*" >> $LOGFILE
}

writelog "Starting"
while true ; do
  runscript
  writelog "Exited with status $?"
  sleep 1
  writelog "Restarting"
done
IFS="$OIFS"