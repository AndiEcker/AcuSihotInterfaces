set log_name=LIVE_%date:~6,4%_%date:~3,2%_%date:~0,2%__%time:~0,2%_%time:~3,2%_%time:~6,2%.log
set log_name=%log_name: =0%
SihotMigration.exe --acuDSN=SP.WORLD --serverIP=tf-sh-sihot1v.acumen.es --resHistory=1 --debugLevel=0 --clientsFirst=1 --breakOnError=0 -L=log\Mig%log_name%
