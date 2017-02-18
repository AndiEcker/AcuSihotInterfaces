# Interfaces between Sihot.PMS and Acumen

>Tools and processes for to migrate and synchronize system configuration, room status, clients and reservations between Sihot.PMS and Acumen.

## Available Commands

This interface suite project is including the following command line tools:

| Command | Description | Used Sihot.PMS Interfaces |
| :--- | :--- | :---: |
| AcuServer | Synchronize changes from Sihot.PMS onto Acumen | Web, Sxml |
| KernelGuestTester | Client/Guest interface testing tool | Kernel |
| MatchcodeToObjId | Get guest OBJID from passed matchcode | Kernel |
| SihotMigration | Migration of clients and reservations from Acumen to Sihot.PMS | Kernel, Web |
| SihotResImport | Import Thomas Cook (Scandinavian) R*.txt files into Sihot.PMS | Kernel, Web |
| SihotResSync | Synchronize clients and reservations changed in Sihot.PMS onto Acumen | Kernel, Web |
| TestConnectivity | Test connectivity to SMTP and Acumen/Oracle servers | - |
| WatchPupPy | Periodically execute and supervise command | - |
| WebRestTester | Reservation interface testing tool | Web |

### Command line arguments

Most of the available commands are using the same command line options. The following command line options are available (sorted by the long name of the option - displayed in the first column):

| Option | Description | Default | Short option | Commands |
| --- | --- | --- | --- | --- |
| acuUser | User name of Acumen/Oracle system | SIHOT_INTERFACE | u | AcuServer, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| acuPassword | User account password on Acumen/Oracle system | - | p | AcuServer, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| acuDSN | Data source name of the Acumen/Oracle database system | SP.TEST | d | AcuServer, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| breakOnError | Abort importation if an error occurs (0=No, 1=Yes) | 0 | b | SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| client | Acumen client reference / Sihot matchcode to be sent | - | c | KernelGuestTester |
| clientsFirst | Migrate first the clients then the reservations (0=No, 1=Yes) | 0 | q | SihotMigration, SihotResSync |
| cmdLine | Command [line] to execute | - | x | WatchPupPy |
| cmdInterval | Command interval in seconds | 3600 | s | WatchPupPy |
| debugLevel | Display additional debugging info on console output (0=disable, 1=enable, 2=verbose) | 0 | D | (all) |
| envChecks | Number of environment checks per command interval | 4 | n | WatchPupPy |
| help | Show help on all the available command line argument options | - | h | (all) |
| logFile | Duplicate stdout and stderr message into a log file | - | L | (all) |
| mapClient | Guest/Client mapping of xml to db items | MAP_CLIENT_DEF | m | SihotResImport, SihotResSync |
| mapRes | Reservation mapping of xml to db items | MAP_RES_DEF | n | SihotResImport, SihotResSync |
| matchcode | Guest matchcode to convert to the associated object ID | - | m | MatchcodeToObjId |
| rciPath | Import path and file mask for RCI CSV-tci_files | C:/RCI_Import/*.csv | y | SihotResImport |
| resHistory | Migrate also the clients reservation history (0=No, 1=Yes) | 1 | r | SihotMigration |
| serverIP | IP address of the interface server | localhost | i | AcuServer, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| serverPort | IP port of the WEB/Sxml interface of this server | 14777 | w | AcuServer, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| serverKernelPort | IP port of the KERNEL interface of this server | 14772 | k | KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| smtpServerUri | SMTP error notification server URI [user[:pw]@]host[:port] | - | c | AcuServer, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| smtpFrom | SMTP Sender/From address | - | f | AcuServer, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| smtpTo | List/Expression of SMTP Receiver/To addresses | - | r | AcuServer, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| tciPath | Import path and file mask for Thomas Cook R*.TXT-tci_files | C:/TourOp_Import/R*.txt | j | SihotResImport |
| timeout | Timeout in seconds for TCP/IP connections | 39.6 | t | AcuServer, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| useKernelForClient | Used interface for clients (0=web, 1=kernel) | 1 | g | SihotResImport, SihotResSync |
| useKernelForRes | Used interface for reservations (0=web, 1=kernel) | 0 | z | SihotResImport, SihotResSync |
| warningsMailToAddr | List/Expression of warnings SMTP receiver/to addresses (if differs from smtpTo) | - | v | SihotResImport, SihotResSync |
| xmlEncoding | Charset used for the xml data | cp1252 | e | AcuServer, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |

Currently all the 26 ascii lower case letters are used for the command line argument short options (apart from `| l |` which is throwing the exception `argparse.ArgumentError: conflicting option string: -l`).


## System Configurations And Mappings

Most of the configuration keys/options and mapping tables are stored within the Lookup Tables (`T_LU`) of the Oracle database of the Acumen server. Others are stored in newly added columns within other Acumen configuration tables. Some are hard coded within the Acumen Oracle views (e.g. V_ACU_RES_DATA). Default values for the command line arguments can be specified within different Configuration files (with the file extensions INI or CFG).

### Hotel IDs

The `SIHOT_HOTELS` lookup class is mapping the Acumen hotel IDs (3 characters stored in the column `LU_ID`) onto the numeric Sihot Hotel Ids (stored in `LU_NUMBER`). Additionally this lookup class is used for to configure the currently active hotels in the Sihot system (initially only ANY/999, BHC/1 and PBC/4):

| Acumen Hotel Code | Resort Name | Currently Active (1=yes, 0=no) | Sihot Hotel Id |
| :---: | :--- | :---:  | :---: |
| ANY | Pseudo hotel for unspecified resort bookings in Tenerife | 1 | 999 |
| ARF | Angler's Reef | 0 | 101 |
| BHC | Beverly Hills Club  / The Suites At Beverly Hills | 1 | 1 |
| BHH | Beverly Hills Heights | 0 | 2 |
| DBD | Dorrabay | 0 | 102 |
| GSA | Golden Sands | 0 | 103 |
| HMC | Hollywood Mirage Club | 0 | 3 |
| KGR | Kentisbury Grange | 0 | 104 |
| LVI | Luna Villas | 0 | 105 |
| PBC | Palm Beach Club | 1 | 4 |
| PLA | Platinum Sports Cruisers | 0 | 106 |
| PMA | Paramount | 0 | 107 |
| PMY | The Palmyra | 0 | 108 |
| PSF | Podere San Filippo | 0 | 109 |
| RHF | Rhinefield Apartments | 0 | 110 |
| CPS | CP Suites in BHC | 0 | 199 |


### Room Categories

The Acumen reservation requests are mainly classified by the room size and requested apartment features, whereas the Sihot.PMS room categories are need to be setup for to include room size and features.

There are several lookup classes with the lookup class name prefix `SIHOT_CATS_` within the Acumen/Oracle lookup table for to map/transform the Acumen unit sizes and optionally also requested apartment features into Sihot room categories. These mappings can be setup for each hotel individually and the pseudo hotel ANY can be used as fallback for all real hotels. Therefore the ANY hotel need to specify at least one mapping/transformation for all available Acumen room/unit sizes: HOTEL/STUDIO/1...4 BED.

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| HOTEL | - | HOTU |
| STUDIO | - | STDO |
| 1 BED | - | 1JNR |
| 2 BED | - | 2BSU |
| 2 BED | High Floor/757 | 2BSH |
| 3 BED | - | 3BPS |


#### BHC room category overloads

The `SIHOT_CATS_BHC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in hotel 1:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| STUDIO | High Floor/757 | STDS |
| 1 BED | Duplex/752 | 1DSS |
| 1 BED | High Floor/757 | 1JNS |
| 2 BED | Duplex/752 | 2DPU |


#### PBC room category overloads

The `SIHOT_CATS_PBC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in hotel 4:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| STUDIO | - | STDP |
| STUDIO | High Floor/757 | STDH |
| STUDIO | Sea View/Front/781 | STDB |
| 1 BED | - | 1JNP |
| 1 BED | High Floor/757 | 1JNH |
| 1 BED | Sterling/748 | 1STS |
| 2 BED | - | 2BSP |
| 2 BED | High Floor/757 | 2BSH |
| 3 BED | - | 3BPB |


#### Room specific overloads

The two new `T_AP` columns `AP_SIHOT_CAT` and `AP_SIHOT_HOTEL` can be used for the individual mapping of each apartment onto a specific Sihot.PMS Hotel Id and Room Price Category (room size and paid supplements).

Specially the Hotel Id mapping will be needed for the 16 BHC sweets that are planned to be migrated to new Club Paradiso pseudo resort.



### Language / Nationality

The mapping of the language and nationalities is done by storing the Sihot language IDs in the Acumen `T_LG` table (`LG_SIHOT_LANG VARCHAR2(2 BYTE)`).

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

The Acumen Reservation Booking Types (ResOcc types) are mapped onto the Sihot Market Segments with the help of 6 new `T_RO` columns.

| column name | column content |
| --- | --- |
| RO_SIHOT_MKT_SEG | SIHOT market segment mapping (lower case not working in SIHOT) |
| RO_SIHOT_RES_GROUP | SIHOT market CHANNEL mapping |
| RO_SIHOT_SP_GROUP | SIHOT market NN mapping |
| RO_SIHOT_AGENCY_OBJID | SIHOT company object ID for agency bookings |
| RO_SIHOT_AGENCY_MC | SIHOT company matchcode for agency bookings |
| RO_SIHOT_RATE | SIHOT Rate for this Market segment and filter flag for every synchronized booking type |


#### Remapped market segment codes

The value in `RO_SIHOT_MKT_SEG` is also optional and only needed if the Acumen Reservation Booking Type code (`RO_CODE`) is different to the Sihot.PMS market segment code. The following table is showing the manual mappings for the Acumen lower-case booking types:

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

The following table shows the mapping between the Sihot CHANNEL field IDs (stored in the `RO_SIHOT_RES_GROUP` column) and the Acumen reservation groups (with the `RO_RES_GROUP` column):

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

The `RO_AGENCY_` columns are needed for to store the Sihot.PMS guest object ids of an optional orderer/agency that will then be used for these types of bookings.
Individual agencies got currently only mapped to the two Thomas Cook booking types: the `TK` (Thomas Cook Scandinavian) bookings got associated to the Sihot guest Object ID `27` and the matchcode `TCRENT` whereas the `tk` (Thomas Cook UK) booking type is associated to the object id `20` and the matchcode `TCAG`.


#### Market Segment Synchronization and Rate

The value within the `RO_SIHOT_RATE` column is not only defining a default rate (Sihot.PMS rate code) for each Reservation Booking Type - it is also used as a flag: if there is a non-empty value then all bookings with this Reservation Booking Type are then automatically included into the synchronization process from Acumen to Sihot.PMS.
The value of the column `RO_SIHOT_RATE` is currently initialized with the following where clause which includes all bookings of our Timeshare Owners, Club Paradiso Members, RCI visitors, Marketing visitors, Thomas Cook visitors and Owner External Rentals:

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

The Thomas Cook bookings are still synchronized in the first project phase for to provide a smooth migration for our Rental Department - although they meanwhile can be imported directly with the SihotResImport command tool into the Sihot.PMS.


### Acumen Client Owner Type Classification

For to minimize the amount of client data to migrate to Sihot.PMS we had to classify the Acumen clients by their type of ownership(s). For each product a owner type can be specified/configured within the new column `RS_SIHOT_GUEST_TYPE`.

The current mapping is setting a general owner flag for to group all timeshare/resort owners together with less important owner types like e.g. tablet, lifestyle, experience or explorer. For special treatment we only need to specify distinguishable client types for Investors (new fractionals/share holders) and Keys Members.


### SIHOT package mappings

The Sihot.PMS Package code can be specified as the value of the key-value attribute `SIHOT_PACK` within the `LU_CHAR` column of each meal plan/board. All Acumen meal plans are stored within the lookup classes `BOARDS` (for all bookings) and `MKT_BOARDS` (only for marketing bookings).

### Thomas Cook Allotment mappings

For to create tour operator bookings via the WEB interface you need to specify the internal number of the allotment contract. This internal allotment contract number is nowhere visible in the GUI of Sihot.PMS and has to be determined by Michael after the creation of the allotment in Sihot.

Each hotel and tour operator has a individual internal allotment contract number. So for our two tour operators Thomas Cook Northern/Scandinavia and U.K. for the two initial hotels (1 and 4) we need to configure four numbers, which are currently specified within the database view `V_ACU_RES_DATA` in the expression of column `SIHOT_ALLOTMENT_NO`. 


### Configuration files

The default values of each command line argument can be set within one of the configurations files. If the values are not specified in the app configuration file then the option default/fallback values will be searched within the base config file: first in the app name section then in the default main section. More information on the several supported configuration files and values you find in the module/package `console_app`.

The following configuration values are not available as command line argument options (can only be specified within a configuration file):
            
| Section Name | Key/Option Name | Description |
| --- | --- | --- |
| Settings | WarningFragments | List of text fragments of complete error messages which will be re-classified as warnings and send separately to the notification receiver (specified in configuration key/option `warningsMailToAddr` or `smtpTo`).



## System Synchronization

Every client that got created first on the Acumen system and then get migrated as guest record onto the Sihot system will by synchronized by the Sihot guest object id. This id will be stored for each pax a our Acumen couple client record in the two new columns `CD_SIHOT_OBJID` and `CD_SIHOT_OBJID2`.

Reservations created first within the Acumen system and then synchronized to Sihot get linked/associated to the Acumen Requested Unit record with the new `T_RU` column `RU_SIHOT_OBJID` for to store Sihot reservation record object id.


### Requested Unit Log

The following 6 new columns got added to the Acumen Requested Unit Log table (`T_RUL`) for to store also any other booking changes of a synchronized reservation that are happening in a associated table like e.g. room change in the related Apartment Reservation (`T_ARO`) or board/meal plan change in the Marketing Prospect (`T_PRC`):

| Column Name | Column Content |
| --- | --- |
| RUL_SIHOT_CAT | Unit/Price category in Sihot.PMS - overloaded if associated ARO exists |
| RUL_SIHOT_HOTEL | Hotel Id in Sihot.PMS - overloaded if associated ARO exists |
| RUL_SIHOT_ROOM | Booked apartment (`AP_CODE`) if associated ARO record exits else NULL |
| RUL_SIHOT_OBJID | `RU_SIHOT_OBJID` value (for to detect if deleted RU got passed into Sihot.PMS) |
| RUL_SIHOT_PACK | Booked package/arrangement - overloaded if associated ARO/PRC exists |
| RUL_SIHOT_RATE | Market segment price rate - used for filtering (also if RU record is deleted) |

These columns got added later on mainly because of performance enhancements by condensing/focusing all these other changes within the latest not synchronized requested unit log entry/record and also for to keep references of deleted `T_RU` records for to be propagated onto Sihot.PMS.


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


# Monitor Application

AcuSihotMonitor is a kivy application that runs on Windows, Linux, Mac OS X, Android and iOS and allows to check the correct functionality of the Acumen and Sihot servers and interfaces.
