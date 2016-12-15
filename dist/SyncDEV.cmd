rem double set needed for to replace leading space in time with hour <= 9 am:
set log_name=DEV_%date:~6,4%_%date:~3,2%_%date:~0,2%__%time:~0,2%_%time:~3,2%_%time:~6,2%.log
set log_name=%log_name: =0%
WatchPupPy.exe --cmdLine="SihotResSync.exe --acuDSN="tf-sh-ora3.acumen.es:1521/@spdev" --serverIP=10.103.222.71 --clientsFirst=0 --breakOnError=0 -D=1 -L=log\Sync%log_name%" --acuDSN="tf-sh-ora3.acumen.es:1521/@spdev" --serverIP=10.103.222.71 -D2 -L=log\SyncWatch%log_name%