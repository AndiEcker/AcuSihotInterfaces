rem double set needed for to replace leading space in time with hour <= 9 am:
set log_name=TEST_%date:~6,4%_%date:~3,2%_%date:~0,2%__%time:~0,2%_%time:~3,2%_%time:~6,2%.log
set log_name=%log_name: =0%
WatchPupPy.exe --cmdInterval=0 --cmdLine="AcuServer.exe --acuDSN=SP.TEST --serverIP=localhost --serverPort=11000 -D=1 -L=log\AcuSrv%log_name%" --acuDSN=""  -D1 -L=log\WatchAcuSrv%log_name%
