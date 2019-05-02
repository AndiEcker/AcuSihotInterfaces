rem reservation interface
md ..\_build_dist\AcuSihotInterfaces\ws_res

copy .sys_envLIVE.cfg ..\_build_dist\AcuSihotInterfaces\ws_res\
copy .sys_envTEST.cfg ..\_build_dist\AcuSihotInterfaces\ws_res\

copy .console_app_env.cfg ..\_build_dist\AcuSihotInterfaces\ws_res\
copy SihotMktSegExceptions.cfg ..\_build_dist\AcuSihotInterfaces\ws_res\
copy SihotServer.py ..\_build_dist\AcuSihotInterfaces\ws_res\app.wsgi
copy SihotServer.ini ..\_build_dist\AcuSihotInterfaces\ws_res\mod_wsgi.ini
copy acif.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy ae_console_app.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy ae_db.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy ae_notification.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy ae_sys_data.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy ae_tcp.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy ass_sys_data.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy sfif.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy shif.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy sxmlif.py ..\_build_dist\AcuSihotInterfaces\ws_res\
copy sys_data_ids.py ..\_build_dist\AcuSihotInterfaces\ws_res\

copy C:\Python35\Lib\site-packages\bottle.py ..\_build_dist\AcuSihotInterfaces\ws_res\

md ..\_build_dist\AcuSihotInterfaces\ws_res\simple_salesforce
copy C:\Python35\Lib\site-packages\simple_salesforce\*.py ..\_build_dist\AcuSihotInterfaces\ws_res\simple_salesforce\*.*
