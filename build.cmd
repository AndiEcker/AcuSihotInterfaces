rem switch to common python build/dist folder for to not pollute the project source folders with build/dist files
cd ..\_build_dist\AcuSihotInterfaces

c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\AcuServer.py
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile --resource ..\..\AcuSihotInterfaces\AcuSihotMonitor.kv ..\..\AcuSihotInterfaces\AcuSihotMonitor.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\AcuSihotMonitor.spec
c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\BssServer.py
c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\ClientQuestionnaireExport.py
rem c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\KernelGuestTester.py
rem c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\MatchcodeToObjId.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\ShSfClientMigration.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\SfClientValidator.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\SihotMigration.py
c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\SihotOccLogChecker.py
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile --resource ..\..\AcuSihotInterfaces\SihotResImport.kv ..\..\AcuSihotInterfaces\SihotResImport.py
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\SihotResImport.spec
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile --resource ..\..\AcuSihotInterfaces\SihotResImport.kv ..\..\AcuSihotInterfaces\SihotResImport.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\SihotResImport.spec
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\SihotResImport_console.spec
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\SihotResSync.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ..\..\AcuSihotInterfaces\SysDataMan.py
c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\TestConnectivity.py
c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\WatchPupPy.py
rem c:\Python35\Scripts\pyinstaller --onefile ..\..\AcuSihotInterfaces\WebResTester.py

rem switch back to project source folder
cd ..\..\AcuSihotInterfaces

rem copy hidden configuration files to dist folder
copy .app_env.cfg ..\_build_dist\AcuSihotInterfaces\dist\
copy .sys_envLIVE.cfg ..\_build_dist\AcuSihotInterfaces\dist\
copy .sys_envTEST.cfg ..\_build_dist\AcuSihotInterfaces\dist\

rem finally also BUILD/copy to web service distribution folders
.\build_ws_test.cmd
.\build_ws_res.cmd
