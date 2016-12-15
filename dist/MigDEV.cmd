rem double set needed for to replace leading space in time with hour <= 9 am:
set log_name=DEV_%date:~6,4%_%date:~3,2%_%date:~0,2%__%time:~0,2%_%time:~3,2%_%time:~6,2%.log
set log_name=%log_name: =0%
REM C:\Python34\python.exe SihotMigration.py --acuDSN=SP.DEV --clientsFirst=1 --breakOnError=0 --debugLevel=2 > log\Mig%log_name% 2>&1
C:\Python34\python.exe SihotMigration.py --acuDSN="tf-sh-ora3.acumen.es:1521/@spdev" --serverIP=10.103.222.71 --resHistory=0 --clientsFirst=1 --breakOnError=0 -D=2 -L=log\Mig%log_name%
