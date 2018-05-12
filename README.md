# Interfaces between Sihot.PMS, Acumen and Salesforce

>Tools and processes for to migrate and synchronize system configuration, room status, clients and reservations 
between Sihot.PMS, Acumen and Salesforce.

## Available Commands

This interface suite project is including the following commands/tools - most of them are command line applications,
apart from AcuSihotMonitor and SihotResImport, which are providing a Kivy user interface:

| Command | Description | Used Sihot.PMS Interfaces |
| :--- | :--- | :---: |
| AcuServer | Synchronize changes from Sihot.PMS onto Acumen | Sxml, Web |
| [AcuSihotMonitor](#acusihotmonitor-application) | Monitor the Acumen and Sihot interfaces and servers | Kernel, Web, Sxml |
| [AssCacheSync](#asscachesync-application) | Initialize, pull, verify or push the AssCache data against Acumen, Sihot and/or Salesforce | Web |
| AssServer | Listening to Sihot SXML interface for to synchronize reservation changes onto the ass_cache PG database | Sxml, Web |
| [ClientQuestionnaireExport](#clientquestionnaireexport-application) | Export check-outs from Sihot to CSV file | Web |
| KernelGuestTester | Client/Guest interface testing tool | Kernel |
| MatchcodeToObjId | Get guest OBJID from passed matchcode | Kernel |
| SfClientValidator | Salesforce Client Data Validator | - |
| ShSfClientMigration | Migrate guests from Sihot to Salesforce | Web |
| SihotMigration | Migration of clients and reservations from Acumen to Sihot.PMS | Kernel, Web |
| [SihotOccLogChecker](#sihotocclogchecker-application) | Sihot SXML interface log file checks and optional Acumen room occupation status fixes | Sxml |
| [SihotResImport](#sihotresimport-application) | Import/Update/Cancel reservations from CSV/TXT files in Sihot.PMS | Kernel, Web |
| SihotResSync | Synchronize clients and reservations changed in Sihot.PMS onto Acumen | Kernel, Web |
| TestConnectivity | Test connectivity to SMTP and Acumen/Oracle servers | - |
| WatchPupPy | Periodically execute and supervise command | - |
| WebRestTester | Reservation interface testing tool | Web |


### General installation instructions

Most of the command line tools don't have a GUI (graphical user interface) - these need only to be distributed/provided
into any folder where the user has execution permissions (e.g. in Windows in C:\Program Files or on any network drive).

For applications of this project with an GUI (like e.g. SihotResImport or AcuSihotMonitor) please first copy the EXE
file and KV file of the application to any folder where the user has execution privileges. Then the following steps need 
to be done to install it for each single user on the users machine:

* Create a new folder with the name if the application (e.g. SihotResImport) under %LOCALAPPDATA% (in Windows situated
 normally under C:\users\<user name>\AppData\Local\ if the user has the profile on the local C: drive, else within the
 AppData\Local folder of the user profile located on our servers).

* Copy the INI file of the application (e.g. SihotResImport.ini) into this folder (created in the last step).

* Create a new shortcut on the user’s desktop with the application name (e.g. “Sihot Reservation Import”). Then within
 the target field put the full absolute path to application EXE file (e.g. “U:\tools\SihotResImport\SihotResImport.exe”).
 And finally put the path of the new folder created in the first step (e.g. “C:\Users\<user name>\AppData\Local\SihotResImport”) 
 into the Start In field of the shortcut. 

 
### General command line arguments

Most of the available commands are using the same command line options. All names of the following command line options
are case-sensitive. The following table is listing them sorted by the option name (see the first column named Option):

| Option | Description | Default | Short option | Commands |
| --- | --- | --- | --- | --- |
| acuUser | User name of Acumen/Oracle system | SIHOT_INTERFACE | u | AcuServer, AcuSihotMonitor, AssCacheSync, KernelGuestTester, SihotMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| acuPassword | User account password on Acumen/Oracle system | - | p | AcuServer, AcuSihotMonitor, AssCacheSync, KernelGuestTester, SihotMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| acuDSN | Data source name of the Acumen/Oracle database system | SP.TEST | d | AcuServer, AcuSihotMonitor, AssCacheSync, KernelGuestTester, SihotMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| addressesToValidate | Post addresses to be validated (invalidated, not validated, ...) | - | A | SfClientValidator |
| breakOnError | Abort importation if an error occurs (0=No, 1=Yes) | 0 | b | SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| client | Acumen client reference / Sihot matchcode to be sent | - | c | KernelGuestTester |
| clientsFirst | Migrate first the clients then the reservations (0=No, 1=Yes) | 0 | q | SihotMigration, SihotResSync |
| correctAcumen | Correct/Fix Acumen data (0=No, 1=Yes) | 0 | A | SihotOccLogChecker |
| cmdLine | Command [line] to execute | - | x | WatchPupPy |
| cmdInterval | Command interval in seconds | 3600 | s | WatchPupPy |
| dateFrom | Start date/time of date range | (depends on command) | F | ClientQuestionnaireExport, ShSfClientMigration, SihotOccLogChecker |
| dateTill | End date/time of date range | (depends on command) | T | ClientQuestionnaireExport, ShSfClientMigration, SihotOccLogChecker |
| debugLevel | Display additional debugging info on console output (0=disable, 1=enable, 2=verbose, 3=verbose with timestamp) | 0 | D | (all) |
| emailsToValidate | Emails to be validated (invalidated, not validated, ...) | not validated | E | SfClientValidator |
| envChecks | Number of environment checks per command interval | 4 | n | WatchPupPy |
| exportFile | full path and name of the export CSV file | - | x | ClientQuestionnaireExport |
| filterFields | Filter to restrict used fields of (C=clients, P=products, R=reservations) | - | Y | AssCacheSync |
| filterRecords | Filter to restrict processed (C=client, P=product, R=reservation) records | - | X | AssCacheSync |
| filterSfClients | Additional WHERE filter clause for Salesforce SOQL client fetch query | W | SfClientValidator |
| filterSfRecTypes | List o fSalesforce client record type(s) to be processed | ['Rentals'] | R | SfClientValidator |
| help | Show help on all the available command line argument options | - | h | (all) |
| includeCxlRes | Include also cancelled reservations (0=No, 1=Yes) | 0 | I | SihotMigration |
| init | Initialize/Recreate postgres AssCache database (0=No, 1=Yes) | 0 | I | AssCacheSync |
| jsonPath | Import path and file mask for OTA JSON files | C:/JSON_Import/R*.txt | j | SihotResImport |
| logFile | Duplicate stdout and stderr message into a log file | - | L | (all) |
| mapClient | Guest/Client mapping of xml to db items | MAP_CLIENT_DEF | m | SihotResImport, SihotResSync |
| mapRes | Reservation mapping of xml to db items | MAP_RES_DEF | n | SihotResImport, SihotResSync |
| matchcode | Guest matchcode to convert to the associated object ID | - | m | MatchcodeToObjId |
| matchFields | Specify field(s) used for to match/lookup the associated data record | - | Z | AssCacheSync |
| matchRecords | Restrict processed (dict keys: C=client, P=product, R=reservation) destination records | - | M | AssCacheSync |
| migrationMode | Skip room swap and hotel movement requests (0=No, 1=Yes) | - | M | SihotResSync |
| pgUser | User account name for the postgres database | 'postgres' | U | AssCacheSync, AssServer |
| pgPassword | User account password for the postgres database | - | P | AssCacheSync, AssServer |
| pgDSN | Database name of the postgres database | ass_cache | N | AssCacheSync, AssServer |
| phonesToValidate | Phones to be validated (invalidated, not validated, ...) | - | P | SfClientValidator |
| push | Push/Update (C=Clients, P=Products, R=Reservations) data from AssCache onto Acumen/Salesforce/Sihot | - | W | AssCacheSync |
| rciPath | Import path and file mask for RCI CSV-tci_files | C:/RCI_Import/*.csv | Y | SihotResImport |
| sfClientId | Salesforce client/application name/id | SignalliaSfInterface/cae.app_name() | C | AssCacheSync, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfIsSandbox | Use Salesforce sandbox (instead of production) | True | s | AssCacheSync, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfPassword | Salesforce user account password | - | a | AssCacheSync, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfToken | Salesforce user account token | - | o | AssCacheSync, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfUser | Salesforce account user name | - | y | AssCacheSync, SfClientValidator, ShSfClientMigration, SihotResImport |
| shClientPort | IP port of the Sxml interface of this server | 11000 (AcuServer) or 12000 (AssServer) | w | AcuServer, AssServer |
| shServerIP | IP address of the Sihot interface server | localhost | i | AcuServer, AcuSihotMonitor, AssCacheSync, AssServer, ClientQuestionnaireExport, KernelGuestTester, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shServerPort | IP port of the WEB interface of the Sihot server | 14777 | w | AcuSihotMonitor, AssCacheSync, ClientQuestionnaireExport, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shServerKernelPort | IP port of the KERNEL interface of this server | 14772 | k | AcuSihotMonitor, AssCacheSync, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shTimeout | Timeout in seconds for TCP/IP connections | 69.3 | t | AcuServer, AcuSihotMonitor, AssCacheSync, AssServer, ClientQuestionnaireExport, KernelGuestTester, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shXmlEncoding | Charset used for the xml data | cp1252 | e | AcuServer, AcuSihotMonitor, AssCacheSync, AssServer, ClientQuestionnaireExport, KernelGuestTester, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| syncDateRange | Restrict sync. of res. to: H=historical, M=present and 1 month in future, P=present and all future, F=future only, Y=present and 1 month in future and all for hotels 1 4 and 999, Y<nnn>=like Y plus the nnn oldest records in the sync queue | - | R | SihotMigration, SihotResSync |
| pull | Pull from (ac=Acumen, sh=Sihot, sf=Salesforce) the (C=Clients, P=Products, R=Reservations) into AssCache | - | S | AssCacheSync |
| smtpServerUri | SMTP error notification server URI [user[:pw]@]host[:port] | - | c | AcuServer, AssCacheSync, AssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| smtpFrom | SMTP Sender/From address | - | f | AcuServer, AssCacheSync, AssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| smtpTo | List/Expression of SMTP Receiver/To addresses | - | r | AcuServer, AssCacheSync, AssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| tciPath | Import path and file mask for Thomas Cook R*.TXT-tci_files | C:/TourOp_Import/R*.txt | j | SihotResImport |
| useKernelForClient | Used interface for clients (0=web, 1=kernel) | 1 | g | SihotResImport, SihotResSync |
| useKernelForRes | Used interface for reservations (0=web, 1=kernel) | 0 | z | SihotResImport, SihotResSync |
| verify | Verify/Check ass_cache database against (ac=Acumen, sh=Sihot, sf=Salesforce) for (C=Clients, P=Products, R=Reservations) data | - | V | AssCacheSync |
| warningsMailToAddr | List/Expression of warnings SMTP receiver/to addresses (if differs from smtpTo) | - | v | AssCacheSync, AssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync |

Currently all the 26 ascii lower case letters are used for the command line argument short options, some of them are
hard-coded by python (like e.g. the -h switch for to show the help screen). The upper case character options -D and -L
are hard-coded by the ae_console_app module. Some options like -m are used and interpreted differently in several
command line applications.

The following lower case letters could be used more easily as short options than others (for to prevent duplicates/conflicts)
for future/upcoming command line options with less conflicts: | l | m | n | q |.


### AcuSihotMonitor Application

AcuSihotMonitor is a kivy application for Windows, Linux, Mac OS X, Android and iOS and allows to check
the correct functionality of the Salesforce, Acumen and Sihot servers and interfaces.


### AssCacheSync Application

AssCacheSync is a command line tool for to pull, push, verify data between the Postgres database AssCache and the
Acumen, Salesforce and/or Sihot systems.


### ClientQuestionnaireExport Application

ClientQuestionnaireExport is a command line tool that exports all check-outs within a given date range into a CSV file
for to be sent to a service company for to do the client questionnaires. FYI: this tools is replacing the currently
used Oracle procedure SALES.TRIPADVISOR (runs every Tuesday around 11 am). There is a similar export available
within the Sihot.PMS EXE application via the menu entry `Export / Export stays for Marketing` (with the checkbox
`Email filter` checked) which is exporting a CSV file into the folder U:/transfer/staysformarketing/.

#### HotelNames INI/config section

This section are defining the hotel names that will be included into the CSV file. The variable name is the Sihot
hotel id. Only the check-outs of hotels that have a hotel name defined will be exported/included in the CSV file.

Currently only the PBC and BHC hotels are processed.

#### HotelLocationIds INI/config section

This section are defining the location ids used by the client questionnaire service for to be included into the
CSV file. The variable name is the Sihot hotel id. Only the check-outs of hotels that have a location id 
defined will be exported/included in the CSV file.

The location IDs provided are 535055 for the BHC hotel and 288275 for the PBC hotel.

#### columnSeparator INI/config setting

Allows to specify the character used for to separate the columns of the CSV file. The default value is the comma (`,`).

#### maxLengthOfStay INI/config setting

Because the Sihot WEB interface is only allowing to search for arrival dates a maximum length of a stay can be
specified for to include them into the exported CSV file. The default value is 42 days.

#### resSearchFlags INI/config setting

Allows to specify the flags provided by the Sihot WEB interface `RES-SEARCH` command. The default value is `ALL-HOTELS`.

#### resSearchScope INI/config setting

Allows to specify the scope flags provided by the Sihot WEB interface `RES-SEARCH` command. The default value is 
`NOORDERER;NORATES;NOPERSTYPES`.

#### fileCaption INI/config setting

Allows to specify/change the header/caption of the exported CSV file. The default value is 
`UNIQUEID,CHECKIN,CHECKOUT,FIRSTNAME,LASTNAME,EMAIL,CITY,COUNTRY,RESORT,LOCATIONID,STAYMONTH,STAYYEAR,LANGUAGE`.

#### fileColumns INI/config setting

Allows to specify/change the content of the data row columns exported CSV file. The default value is
`['<unique_id>', 'ARR', 'DEP',
  LIST_MARKER_PREFIX + 'NAME2', LIST_MARKER_PREFIX + 'NAME',
  LIST_MARKER_PREFIX + 'EMAIL', LIST_MARKER_PREFIX + 'CITY',
  LIST_MARKER_PREFIX + 'COUNTRY', '<hotel_id_to_name(hotel_id)>',
  '<hotel_id_to_location_id(hotel_id)>',  # '<"xx-0000-xx">',
  '<check_out.month>', '<check_out.year>',
  'LANG',
  ]`.


### SihotOccLogChecker Application

This command line tool is helping to check and optionally fix any missing occupation data changes (like Room-Checkin,
-Checkout or -Move) within the Acumen system.

The tool is parsing each Check-In (CI), Check-Out (CO) and Room.Move (RM) in the Sihot SXML interface log file for to
compare it with the Acumen data. There will be lots of discrepancies shown for reservations that are imported
into Sihot via Siteminder or created manually (because they not existing in Acumen). Therefore on the first run you only
need to the check the summary at the end of the console output (as well as at the end of the log file, created mostly
in the log sub-folder). 

The summary consists e.g. of the number of fixable reservations - if this value is zero than everything is ok, because
there is nothing that this tool could repair for you. A few line above you should double check if there any gaps between
the specified date range and the log entry timestamps within the specified log file.

Occupation data changes done in Sihot get normally transferred via the Sihot SXML interface first to the AcuServer 
and from there to the Acumen system. So if either the SXML interface
or the AcuServer is not running correctly (like happened recently between 16/10/2017 14:07:32 and 18/10/2017 15:09:53),
then you can use SihotOccLogChecker for to check and repair the related T_ARO data in Acumen.

So for to check the discrepancies for the above date range you have to provide the exact date range with the
command line options `dateFrom` and `dateTill` to SihotOccLogChecker, like shown underneath:

`--dateFrom="2017-10-16 14:07:33.0" -dateTill="2017-10-18 15:09:52.0"`

The default value for `dateFrom` is yesterday at the same time and for `dateTill` it is the current time.

Additionally you have to specify the Acumen server with the `acuDSN` command line option, the Acumen user name and
password with the `acuUser` and `acuPassword` command line options and finally the path and filename of the Sihot
SXML log file as command line parameter (e.g. `E:\sihot\log\SP\SXML_ACUMEN@SP.log` directly from our Sihot production
 server or `\\<sihot-server>\e$\sihot\log\sp\SXML_ACUMEN@SP.log` from the network).

After checking the discrepancies you can add the `correctAcumen` command line option for to fix the Acumen
occupation status. If you want for example to fix the missing occupation changes in our second big outage (between
21/10/2017 17:54:38 and 23/10/2017 10:20:50) in Acumen you have to specify the following command line arguments: 

`-F="2017-10-21 17:54:38.0" -T="2017-10-23 10:20:50.0" -A=1 -u=AECKER -p=password -d=SP.WORLD`

In the last example the short options got used (see the Short Option column in the section
[General command line arguments](#general-command-line-arguments) above). For a more verbose output you can also
pass the `debugLevel` command line option (or as short option -D) with a value of 2 (for verbose) or 3 (verbose and
with timestamp).

#### maxDaysDiff INI/config setting

Allows to specify the maximum number of days of difference between the expected and the real check-in/-out day. The
default value is 2 days. FYI: the Oracle procedure P_SIHOT_ALLOC() that is used by AcuServer to pass occupation
changes to Acumen is using 4 days of difference (see constant SihotRoomChangeMaxDaysDiff declared in the K package).

#### daysCheckInBefore INI/config setting

This config variable allows this tool to search also for Acumen reservations that got checked-in the given number
of days before the expected arrival date.
 
Please note that the value of this setting is restricted by the value of the maxDaysDiff INI/config setting (see above).

#### daysCheckOutAfter INI/config setting

This config variable allows this tool to search also for Acumen reservations that got checked-out the given number
of days after the expected departure date.

Please note that the value of this setting is restricted by the value of the maxDaysDiff INI/config setting (see above).


### SihotResImport Application

Combined Console/Kivy Application for to import reservation bookings, changes and cancellations from CSV or JSON files
into the Sihot system.

Apart from the instruction in the [General Installation Instructions](#general-installation-instructions)_ section (see
above) you also have to create an import path folder for each supported import channel (e.g. C:\JSON_Import). The same
path name has to be specified as command line argument when you start the SihotResImport application (see next 
paragraph). Please note that the user need to have full access (read, write and create folder privileges) within each 
of these import channel folders. 

The provided command line options are documented above in the section
[General command line arguments](#general-command-line-arguments). The most important one is the `jsonPath` option, 
for to specify the import path and file mask for OTA JSON files - this value defaults to `C:/JSON_Import/*.json`.

For to run this application in console mode (headless without any user interface), simply specify a valid 
Acumen user name (acuUser) and password (acuPassword) as command line parameters (or via one of supported config/INI files).

There are four command line parameters specifying the used Sihot server (production or test): `shServerIP` is the DNS name
or IP address of the SIHOT interface server, `shServerPort` is the IP port of the used WEB interface and optionally
you can specify via `timeout` the timeout value in seconds for TCP/IP connections (default=69.3) and via `shXmlEncoding`
the charset encoding used for the xml data (default='cp1252').

Meanwhile and for to check the client data against our Salesforce system this application needs also a user account for
the Salesforce system. If you start this application using E:\AcuServer\ of the Sihot production system as the current
working directory then you don't need to specify anything to use the Salesforce sandbox, but for production you need at
least to specify the user name (sfUser), the security token (sfToken), the sandbox flag set to False (sfIsSandbox=False)
and the password (the password can be omitted if you use our SihotInterface user account).

Another four command line parameters are for to configure the notification emails: `smtpServerUri` specifies the 
SMTP server URI (including user name, password, host and port). The sender address has to be specified by
`smtpFrom`, the list of SMTP receivers by `smtpTo` (for the protocol) and `warningsMailToAddr` (for the
warnings/discrepancy notifications.

By passing the numeric value 1 to the optional command line argument `breakOnError` you could abort the importation
if an error occurs in one of the JSON files.

#### JSON field names

The following section is documenting the available json field names for to be populated with the reservation details 
of each booking coming via email from OTA channels that are not supported by Siteminder (the tool to convert each
email into the json format is written in C#.NET by Nitesh): 

| Field Name | Field Type | Description | Example Values |
| --- | --- | --- | --- |
| RUL_SIHOT_HOTEL | Numeric | Sihot Hotel Id | 1=PBC, 4=BHC |
| SH_RES_TYPE | Char | Sihot Reservation Type | 'S'=cancelled, '1'=guaranteed |
| RUL_ACTION | String | Reservation Booking Action | 'INSERT'=new booking, 'UPDATE'=modified booking, 'CANCEL'=cancellation |
| SIHOT_GDSNO | String | Sihot GDS number | <OTA-channel-prefix><Voucher number>, e.g. 'OTS-abc123456789' |
| RH_EXT_BOOK_REF | String | Sihot Voucher number / OTA channel booking reference | 'abc123456789' |
| RH_EXT_BOOK_DATE | Date | Sihot Reservation Booking Date | 24-12-2016 |
| ARR_DATE | Date | Arrival Date | 28-02-2017 |
| DEP_DATE | Date | Departure Date | 07-03-2017 |
| RUL_SIHOT_CAT | String | Requested Sihot Room Category | '1STS', '1JNP', '2BSS' |
| SH_PRICE_CAT | String | Paid Sihot Room Category (mostly same as RUL_SIHOT_CAT) | '1STS', '1JNP', '2BSS' |
| RUL_SIHOT_ROOM | String | Sihot Room Number (optional) | '0426', 'A112' |
| SH_OBJID | String | Sihot Orderer Object Id of OTA channel | '123456' |
| OC_SIHOT_OBJID | String | Sihot Orderer Object Id of OTA channel (same as SH_OBJID) | '123456' |
| SH_MC | String | Sihot Orderer Matchcode of OTA channel | 'TCRENT' |
| OC_CODE | String | Sihot Orderer Matchcode of OTA channel (same as SH_MC) | 'TCRENT' |
| SIHOT_NOTE | String | Sihot Reservation Comment (short) | 'extra info' (use ';' for to separate various comments) |
| SIHOT_TEC_NOTE | String | Sihot Reservation Technical Comment (long) | 'extra info' (use '|CR|' for to separate various comments) |
| RUL_SIHOT_PACK | String | Sihot Meal-Plan/Board | 'RO'=room only, 'BB'=Breakfast, 'HB'=Half Board |
| SIHOT_MKT_SEG | String | Sihot Marketing Segment / OTA Channel | 'XY', 'TK', 'TC' |
| SIHOT_RATE_SEGMENT | String | Sihot Price Rate/Segment (mostly same as SIHOT_MKT_SEG, but SIT for Siteminder) | 'XY', 'TK', 'TC' |
| SIHOT_PAYMENT_INST | Numeric | Sihot Payment Instructions | 0=Guest Account, 1=Group Account, 3=Client Account |
| RU_SOURCE | Char | Sihot Reservation Source | 'A'=Admin, 'T'=Tour Operator |
| RO_RES_GROUP | String | Sihot Reservation Channel | 'RS'=Rental SP |
| RU_ADULTS | Numeric | Number of Adults | 1, 2, 4 |
| RU_CHILDREN | Numeric | Number of Children | 0, 1, 2 |
| SH_ADULT1_NAME | String | Surname of first adult | 'Smith' | 
| SH_ADULT1_NAME2 | String | Forename of first adult | 'John' | 
| SH_PERS_SEQ1 | Numeric | Rooming List Person First Adults Sequence Number | 0 | 
| SH_ROOM_SEQ1 | Numeric | Rooming List First Adults Room Sequence Number | 0 | 
| SH_ADULT2_NAME | String | Surname of second adult | 'Miller' | 
| SH_ADULT2_NAME2 | String | Forename of second adult | 'Joanna' |
| SH_PERS_SEQ2 | Numeric | Rooming List Person Second Adults Sequence Number | 1 | 
| SH_ROOM_SEQ2 | Numeric | Rooming List Second Adults Room Sequence Number | 0 | 
| SH_CHILD1_NAME | String | Surname of first children | 'Smith' | 
| SH_CHILD1_NAME2 | String | Forename of first children | 'Paul' | 
| SH_PERS_SEQ11 | Numeric | Rooming List Person First Children Sequence Number | 10 | 
| SH_ROOM_SEQ11 | Numeric | Rooming List First Children Room Sequence Number | 0 | 
| SH_CHILD2_NAME | String | Surname of second children | 'Miller' | 
| SH_CHILD2_NAME2 | String | Forename of second children | 'Debra' |
| SH_PERS_SEQ12 | Numeric | Rooming List Person Second Children Sequence Number | 11 | 
| SH_ROOM_SEQ12 | Numeric | Rooming List Second Children Room Sequence Number | 0 |
| SH_ROOMS | Numeric | Number of Rooms in Rooming List (optional if 1) | 1 | 
| SH_EXT_REF | String | Flight Number (optional) | 'ABC-2345' |
| SIHOT_ALLOTMENT_NO | Numeric | Sihot Allotment Number (optional) | e.g. 11 in BHC, 12 in PBC for Thomas Cook bookings | 
 

## System Configurations And Mappings

Most of the configuration keys/options and mapping tables are stored within the Lookup Tables (`T_LU`) of the Oracle
database of the Acumen server. Others are stored in newly added columns within other Acumen configuration tables.
Some are hard coded within the Acumen Oracle views (e.g. V_ACU_RES_DATA). Default values for the command line arguments
can be specified within different Configuration files (with the file extensions INI or CFG).

### Hotel IDs

The `SIHOT_HOTELS` lookup class is mapping the Acumen hotel IDs (3 characters stored in the column `LU_ID`) onto the
numeric Sihot Hotel Ids (stored in `LU_NUMBER`). Additionally this lookup class is used for to configure the currently
active hotels in the Sihot system (initially only ANY/999, BHC/1 and PBC/4):

| Acumen Hotel Code | Resort Name | Currently Active (Y=yes, n=no) | Sihot Hotel Id |
| :---: | :--- | :---:  | :---: |
| ANY | Pseudo hotel for unspecified resort bookings in Tenerife | Y | 999 |
| ARF | Angler's Reef | n | 101 |
| BHC | Beverly Hills Club  / The Suites At Beverly Hills | Y | 1 |
| BHH | Beverly Hills Heights | Y | 2 |
| DBD | Dorrabay | n | 102 |
| GSA | Golden Sands | n | 103 |
| HMC | Hollywood Mirage Club | Y | 3 |
| KGR | Kentisbury Grange | n | 104 |
| LVI | Luna Villas | n | 105 |
| PBC | Palm Beach Club | Y | 4 |
| PLA | Platinum Sports Cruisers | n | 106 |
| PMA | Paramount | n | 107 |
| PMY | The Palmyra | n | 108 |
| PSF | Podere San Filippo | n | 109 |
| RHF | Rhinefield Apartments | n | 110 |
| CPS | CP Suites in BHC | n | 199 |


### Room Categories

The Acumen reservation requests are mainly classified by the room size and requested apartment features, whereas the
Sihot.PMS room categories are need to be setup for to include room size and features.

There are several lookup classes with the lookup class name prefix `SIHOT_CATS_` within the Acumen/Oracle lookup table
(or alternatively meanwhile also in the `ResortCats` section of the *.CFG/*.INI configuration files of this suite)
for to map/transform the Acumen unit sizes and optionally also requested apartment features into Sihot room categories.
These mappings can be setup for each hotel individually and the pseudo hotel ANY can be used as fallback for all real
hotels. Therefore the ANY hotel need to specify at least one mapping/transformation for all available Acumen room/unit
sizes: HOTEL/STUDIO/1...4 BED.

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| HOTEL | - | HOTU |
| STUDIO | - | STDO |
| 1 BED | - | 1JNR |
| 2 BED | - | 2BSU |
| 2 BED | High Floor/757 | 2BSH |
| 3 BED | - | 3BPS |


#### BHC room category overloads

The `SIHOT_CATS_BHC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 1:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| HOTEL | - | HOTU |
| STUDIO | High Floor/757 | STDS |
| 1 BED | Duplex/752 | 1DSS |
| 1 BED | High Floor/757 | 1JNS |
| 2 BED | - or Duplex/752 | 2DPU |
| 2 BED | High Floor/757 | 2BSH |


#### BHH room category overloads

The `SIHOT_CATS_BHH` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 2:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| 1 BED | - | 1JNP |
| 1 BED | Duplex/752 | 1DDP
| 1 BED | High Floor/757 |  1DDS |
| 1 BED | Sea View/Front/781 |  1JNS|
| 2 BED | - | 2BSP |
| 2 BED | Sterling/748 | 2BSS |
| 2 BED | Duplex/752 | 2DDP |
| 2 BED | High Floor/757 | 2DDP |
| 2 BED | Sea View/Front/781 | 2DDS |
| 3 BED | Duplex/752 | 3BPS |
| 3 BED | High Floor/757 | 3BPS |


#### HMC room category overloads

The `SIHOT_CATS_HMC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 3:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| STUDIO | High Floor/757 | STDS |
| STUDIO | Sea View/Front/781 | STDS |
| 1 BED | - | 1JNP
| 1 BED | Duplex/752 | 1DDS |
| 1 BED | High Floor/757 | 1JNS |
| 1 BED | Sea View/Front/781 | 1DDS |
| 2 BED | - | 2BSP |
| 2 BED | Sterling/748 | 2BSS |
| 2 BED | Duplex/752 | 2DDO |
| 2 BED | High Floor/757 | 2BSS |
| 2 BED | Sea View/Front/781 | 2DDS |
| 3 BED | - | 3DDS |
| 3 BED | Duplex/752 | 3DDS |
| 3 BED | High Floor/757 | 3DDS |
| 3 BED | Sea View/Front/781 | 3DDS |
| 4 BED | - | 4BPS |
| 4 BED | Duplex/752 | 4BPS |
| 4 BED | High Floor/757 | 4BPS |


#### PBC room category overloads

The `SIHOT_CATS_PBC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 4:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| STUDIO | - | STDP |
| STUDIO | High Floor/757 | STDH |
| STUDIO | Sea View/Front/781 | STDB |
| 1 BED | - | 1JNP |
| 1 BED | Sterling/748 | 1STS |
| 1 BED | High Floor/757 | 1JNH |
| 1 BED | Sea View/Front/781 | 1JNB |
| 2 BED | - | 2BSP |
| 2 BED | High Floor/757 | 2BSH |
| 2 BED | Sea View/Front/781 | 22SB |
| 3 BED | - | 3BPB |
| 3 BED | High Floor/757 | 3BPB |
| 3 BED | Sea View/Front/781 | 3BPB |


#### Room specific overloads

The two new `T_AP` columns `AP_SIHOT_CAT` and `AP_SIHOT_HOTEL` can be used for the individual mapping of each apartment
onto a specific Sihot.PMS Hotel Id and Room Price Category (room size and paid supplements).

Specially the Hotel Id mapping will be needed for the 16 BHC sweets that are planned to be migrated to new Club Paradiso
pseudo resort.



### Language / Nationality

The mapping of the language and nationalities is done by storing the Sihot language IDs in the Acumen `T_LG` table
(`LG_SIHOT_LANG VARCHAR2(2 BYTE)`).

| Sihot Id | Acumen Code |
| --- | --- |
| HR | CRO |
| EN | ENG |
| FR | FRE |
| DE | GER |
| IT | ITA |
| PL | POL |
| PT | POR |
| ES | SPA |
| SI | SVN |


### Booking Types Market Segmentation

The Acumen Reservation Booking Types (ResOcc types) are mapped onto the Sihot Market Segments with the help of 6 new
`T_RO` columns.

| column name | column content |
| --- | --- |
| RO_SIHOT_MKT_SEG | SIHOT market segment mapping (lower case not working in SIHOT) |
| RO_SIHOT_RES_GROUP | SIHOT market CHANNEL mapping |
| RO_SIHOT_SP_GROUP | SIHOT market NN mapping |
| RO_SIHOT_AGENCY_OBJID | SIHOT company object ID for agency bookings |
| RO_SIHOT_AGENCY_MC | SIHOT company matchcode for agency bookings |
| RO_SIHOT_RATE | SIHOT Rate for this Market segment and filter flag for every synchronized booking type |


#### Remapped market segment codes

The value in `RO_SIHOT_MKT_SEG` is also optional and only needed if the Acumen Reservation Booking Type code (`RO_CODE`)
is different to the Sihot.PMS market segment code. The following table is showing the manual mappings for the Acumen
lower-case booking types:

| Sihot Market segment ID | Acumen Reservation Booking Type |
| --- | --- |
| FG | fG |
| FO | fO |
| H1 | hg |
| H2 | hG |
| H3 | hR |
| H5 | hr |
| H6 | hW |
| H7 | hw |
| I1 | ig |
| I2 | iG |
| I3 | ii |
| I4 | iI |
| IW | iW |
| RG | rW |
| RN | Ri |
| RP | Ro |
| TS | TC |
| TC | tk |
| T1 | tc |


#### Mapping of Acumen Reservation Group to Sihot Channel

The following table shows the mapping between the Sihot CHANNEL field IDs (stored in the `RO_SIHOT_RES_GROUP` column)
and the Acumen reservation groups (with the `RO_RES_GROUP` column):

| Acumen Reservation Group | Sihot Channel Id |
| --- | --- |
| Club Paradiso Guest | CG |
| Club Paradiso Owner | CO |
| Other | OT |
| Owner | OW |
| Owner Guest | OG |
| Promo | FB |
| RCI External | RE |
| RCI External Guest | RG |
| RCI Internal | RI |
| RCI Owner Guest | RO |
| Rental External | RR |
| Rental SP | RS |


#### Mapping of Acumen SP Group to Sihot NN

Underneath the mapping of the Sihot NN field (`RO_SIHOT_SP_GROUP`) onto the Acumen Silverpoint Groups (`RO_SP_GROUP`):

| Acumen SP Group | Sihot NN Id |
| --- | --- |
| Rental SP | RS |
| SP Booking | SB |
| SP CP Booking | SC |
| SP PB Booking | SP |


#### Orderer Agency Configuration for each Market Segment

The `RO_AGENCY_` columns are needed for to store the Sihot.PMS guest object ids of an optional orderer/agency that will
then be used for these types of bookings.

Individual agencies got currently only mapped to the two Thomas Cook booking types: the `TK` (Thomas Cook Scandinavian)
bookings got associated to the Sihot guest Object ID `27` and the matchcode `TCRENT` whereas the `tk` (Thomas Cook UK)
booking type is associated to the object id `20` and the matchcode `TCAG`.


#### Market Segment Synchronization and Rate

The value within the `RO_SIHOT_RATE` column is not only defining a default rate (Sihot.PMS rate code) for each
Reservation Booking Type - it is also used as a flag: if there is a non-empty value then all bookings with this
Reservation Booking Type are then automatically included into the synchronization process from Acumen to Sihot.PMS.

The value of the column `RO_SIHOT_RATE` is currently initialized with the following where clause which includes all
bookings of our Timeshare Owners, Club Paradiso Members, RCI visitors, Marketing visitors, Thomas Cook visitors and
Owner External Rentals:

```
 where RO_CLASS in ('B', 'R')
   and (   substr(RO_RES_GROUP, 1, 5) = 'Owner'
        or substr(RO_RES_GROUP, 1, 13) = 'Club Paradiso'
        or substr(RO_RES_GROUP, 1, 3) = 'RCI'
        or substr(RO_RES_GROUP, 1, 5) = 'Promo'
        or RO_CODE in ('TK', 'tk')
        or RO_CODE = 'ER'   -- requested by Esther 03-11-2016
       );
```

The Thomas Cook bookings are still synchronized in the first project phase for to provide a smooth migration for our
Rental Department - although they meanwhile can be imported directly with the SihotResImport command tool into the
Sihot.PMS.


### Acumen Client Owner Type Classification

For to minimize the amount of client data to migrate to Sihot.PMS we had to classify the Acumen clients by their type of
ownership(s). For each product a owner type can be specified/configured within the new column `RS_SIHOT_GUEST_TYPE`.

The current mapping is setting a general owner flag for to group all timeshare/resort owners together with less important owner types like e.g. tablet, lifestyle, experience or explorer. For special treatment we only need to specify distinguishable client types for Investors (new fractionals/share holders) and Keys Members.


### SIHOT package mappings

The Sihot.PMS Package code can be specified as the value of the key-value attribute `SIHOT_PACK` within the `LU_CHAR`
column of each meal plan/board. All Acumen meal plans are stored within the lookup classes `BOARDS` (for all bookings)
and `MKT_BOARDS` (only for marketing bookings).

### Thomas Cook Allotment mappings

For to create tour operator bookings via the WEB interface you need to specify the internal number of the allotment
contract. This internal allotment contract number is nowhere visible in the GUI of Sihot.PMS and has to be determined
by Michael after the creation of the allotment in Sihot. UPDATE: the new version is showing the allotment number.

Each hotel and tour operator has a individual internal allotment contract number. So for our two tour operators Thomas
Cook Northern/Scandinavia and U.K. for the two initial hotels (1 and 4) we need to configure four numbers, which are
now specified within the new config file SihotMktSegExceptions.cfg. 


### Configuration files

The default values of each command line argument can be set within one of the configurations files. If the values are
not specified in the app configuration file then the option default/fallback values will be searched within the base
config file: first in the app name section then in the default main section. More information on the several supported
configuration files and values you find in the module/package `ae_console_app`.

The following configuration values are not available as command line argument options (can only be specified within a
configuration file):
            
| Section Name | Key/Option Name | Description |
| --- | --- | --- |
| Settings | addressValidatorBaseUrl | Base URL for address validation web service |
| Settings | addressValidatorSearchUrl | Search URL for address validation web service |
| Settings | addressValidatorFetchUrl | Fetch URL for address validation web service |
| Settings | addressValidatorApiKey | address validation web service API key |
| Settings | apCats | Room category overloads for single hotel rooms |
| Settings | emailValidatorBaseUrl | Base URL for email validation web service |
| Settings | emailValidatorApiKey | email validation web service API key |
| Settings | hotelIds | Mapping of Sihot/Acumen hotel ids |
| Settings | pgRootUsr | Root user account name for AssCache database |
| Settings | pgRootPwd | Root user account name for AssCache database |
| Settings | phoneValidatorBaseUrl | Base URL for phone number validation web service |
| Settings | phoneValidatorApiKey | phone number validation web service API key |
| Settings | resortCats | Room category defaults and apartment feature overloads for all hotels/resorts |
| Settings | roAgencies | Agency Sihot/Acumen object Ids and market segment groupings |
| Settings | roomChangeMaxDaysDiff | Number of days a check-in/-out/room-move can differ from the expected arrival/departure date |
| Settings | shAdultPersTypes | List of Sihot adult person type categories, e.g. ['1A', '5A'] |
| Settings | shChildPersTypes | List of Sihot children person type categories, e.g. ['2A', '2B', '2C', '6A', '6B', '6C'] |
| Settings | WarningFragments | List of text fragments of complete error messages which will be re-classified as warnings and send separately to the notification receiver (specified in configuration key/option `warningsMailToAddr` or `smtpTo`).
| SihotAllotments | <marketSegmentCode>[_<hotel_id>] | Allotment/contract number for each market segment (and hotel id) |
| SihotPaymentInstructions | <marketSegmentCode> | Sihot Payment Instruction code for each market segment | 
| SihotRateSegments | <marketSegmentCode> | Sihot Rate Segment code for each market segment |
| SihotResTypes | <marketSegmentCode> | Sihot Reservation Type overload code for each market segment |


## System Synchronization

Every client that got created first on the Acumen system and then get migrated as guest record onto the Sihot system
will by synchronized by the Sihot guest object id. This id will be stored for each pax a our Acumen couple client
record in the two new columns `CD_SIHOT_OBJID` and `CD_SIHOT_OBJID2`.

Reservations created first within the Acumen system and then synchronized to Sihot get linked/associated to the Acumen
Requested Unit record with the new `T_RU` column `RU_SIHOT_OBJID` for to store Sihot reservation record object id.


### Requested Unit Log

The following 8 new columns got added to the Acumen Requested Unit Log table (`T_RUL`) for to store also any other
booking changes of a synchronized reservation that are happening in a associated table like e.g. room change in the
related Apartment Reservation (`T_ARO`) or board/meal plan change in the Marketing Prospect (`T_PRC`):

| Column Name | Column Content |
| --- | --- |
| RUL_SIHOT_CAT | Unit/Price category in Sihot.PMS - overloaded if associated ARO exists |
| RUL_SIHOT_HOTEL | Hotel Id in Sihot.PMS - overloaded if associated ARO exists |
| RUL_SIHOT_ROOM | Booked apartment (`AP_CODE` value as Sihot room number - with leading zero for 3-digit PBC room numbers) if associated ARO record exits else NULL |
| RUL_SIHOT_OBJID | `RU_SIHOT_OBJID` value (for to detect if deleted RU got passed into Sihot.PMS) |
| RUL_SIHOT_PACK | Booked package/arrangement - overloaded if associated ARO/PRC exists |
| RUL_SIHOT_RATE | Market segment - used for filtering (also if RU record is deleted) |
| RUL_SIHOT_LAST_CAT | Previous Unit/Price category - needed for cancellation |
| RUL_SIHOT_LAST_HOTEL | Previous Hotel Id - needed for cancellation and hotel moves |

These columns got added later on mainly because of performance enhancements by condensing/focusing all these other
changes within the latest not synchronized requested unit log entry/record and also for to keep references of deleted
`T_RU` records for to be propagated onto Sihot.PMS.


### Synchronization Log

The synchronization process is fully logged within the new `T_SRSL` table providing the following columns:

| Column Name | Column Content |
| --- | --- |
| SRSL_TABLE | Acumen Table ID (RU/ARO/CD) |
| SRSL_PRIMARY | Acumen Table Primary Key (`RU_CODE`/Requested Unit, `ARO_CODE`/Apartment Reservation or `CD_CODE`/Client Details) |
| SRSL_ACTION | Initiated Action/OC=operation-code Onto Sihot.PMS (for CD also action of Person2) |
| SRSL_STATUS | Final Status/Response of Sihot.PMS (synchronized if substr(,1,6)='SYNCED', else 'ERR\[RC-code\]') |
| SRSL_DATE | Date/Time of the insert into this log table |
| SRSL_LOGREF | Audit Trail Log Id (for debugging only) - Primary Key of either RUL/Requested Unit Log, AROL/Apartment Reservation Log or LOG/Client Details Log |
| SRSL_MESSAGE | Final or Error Message/Response of Sihot.PMS (taken from the MSG response xml element) |
