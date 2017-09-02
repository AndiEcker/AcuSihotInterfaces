rem reload migrations of rental clients arrived between 01-08-2017 and 28-08-2017 (yesterday) to Salesforce Contacts
ShSfContactMigration.exe -D=2 --dateFrom=2017-08-01 --dateTill=2017-08-28 --serverIP=10.103.222.52 --sfUser=sihotinterface@signallia.com --sfToken=o9NU99LBgGt8DzhB6ahZMbk4 --sfIsSandbox=False --smtpTo=['ITDevmen@acumen.es'] --warningsMailToAddr=['ITDevmen@acumen.es']
