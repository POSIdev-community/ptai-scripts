#!/bin/sh
# (c) Aleksandr Gadai, https://swordfish-security.ru, 2024

# Increase PT AI docker containers memory limit by percentage (default: 30)
# usage: sh ptaimemlimit.sh 40

PATCH=$(cat <<"EOF"
@@ -34,7 +34,7 @@

   resources_mem="{ "

-  mem_base=$((mem_free / counter / 1024)) #MB
+  mem_base=$((mem_free / counter / 1024 * XXX / 100)) #MB
   print "Memory limits for fallback scenario - %d MB." "$mem_base" | pipe_log | pipe_verbose

   print "Memory limits for containers:" | pipe_log | pipe_verbose
EOF
)

if [ $# -eq 0 ]
  then
    PERCENT=130 # default value
  else
    PERCENT=$(($1 + 100))
fi
if [ "$PERCENT" -gt "100" ] # input check
  then
    printf '%s\n' "$PATCH" | sed "s/XXX/$PERCENT/" > /tmp/reconf.sh.diff # update patch file with percent value
    if [ $? -eq 0 ]
      then
        echo "Patch generation success!"
        cd /opt/ptai/latest # (!) change if your install directory is different
        test -f lib/reconf.sh.bckp || cp lib/reconf.sh lib/reconf.sh.bckp # create backup if it did not exist
        patch -l -f lib/reconf.sh /tmp/reconf.sh.diff # apply patch
        if [ $? -eq 0 ]
          then # restart if patch applied successfully
            ./bin/ptaictl reconf --noconfirm
            ./bin/ptaictl restart --noconfirm
        fi
    else
      echo "Patch generation failed"
    fi
  else
    echo "ERROR: number should be greater than 0"
fi