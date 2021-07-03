rem double set needed to replace leading space in time with hour <= 9 am:
set log_name=_%date:~6,4%_%date:~3,2%_%date:~0,2%__%time:~0,2%_%time:~3,2%_%time:~6,2%.log
set log_name=%log_name: =0%
WatchPupPy.exe --cmdInterval=0 --cmdLine="AcuServer.exe" --sfUser="" -L=log\WatchAcuServer%log_name%
