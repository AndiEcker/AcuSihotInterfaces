select * from audit.logged_actions
 where relid = (SELECT oid FROM pg_class WHERE relname = 'clients' AND relkind = 'r')     --table_name = 'clients' 
   and action_tstamp_stm > '2018-06-14 12:15' --:34.659023+01'
   and action in ('I', 'U', 'D')
   and (row_data @> '"cl_pk"=>"459473"' or row_data @> '"cl_pk"=>"459474"' or row_data @> '"cl_pk"=>"459476"')
 limit 10