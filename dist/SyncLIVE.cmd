rem double set needed for to replace leading space in time with hour <= 9 am:
set log_name=LIVE_%date:~6,4%_%date:~3,2%_%date:~0,2%__%time:~0,2%_%time:~3,2%_%time:~6,2%.log
set log_name=%log_name: =0%
WatchPupPy.exe --cmdInterval=3600 --cmdLine="SihotResSync.exe --acuDSN=SP.WORLD --serverIP=10.103.222.52 --clientsFirst=0 --breakOnError=0 --smtpTo=['reservations@signallia.com','reservations@PalmBeachClubTenerife.com','Reservations@thesuitesatbeverlyhillstenerife.com','ITDevmen@acumen.es'] --warningsMailToAddr=['reservations@signallia.com','reservations@PalmBeachClubTenerife.com','Reservations@thesuitesatbeverlyhillstenerife.com','ITDevmen@acumen.es'] -D=1 -L=log\Sync%log_name%" --acuDSN=SP.WORLD --serverIP=10.103.222.52 --smtpTo=['Reservations@thesuitesatbeverlyhillstenerife.com','reservations@PalmBeachClubTenerife.com','ITDevmen@acumen.es'] -D1 -L=log\SyncWatch%log_name%