set PATH=C:\Python34\;C:\Python34\Scripts;%PATH%

rem NOT WORKING: c:\Python34\Scripts\pyinstaller --onefile --resource AcuSihotMonitor.kv AcuSihotMonitor.py
c:\Python34\Scripts\pyinstaller --onefile AcuServer.py
c:\Python34\Scripts\pyinstaller --onefile AcuSihotMonitor.spec
rem c:\Python34\Scripts\pyinstaller --onefile KernelGuestTester.py
rem c:\Python34\Scripts\pyinstaller --onefile MatchcodeToObjId.py
rem c:\Python34\Scripts\pyinstaller --onefile SihotMigration.py
rem NOT WORKING: c:\Python34\Scripts\pyinstaller --onefile --resource SihotResImport.kv SihotResImport.py
rem NOT WORKING: c:\Python34\Scripts\pyinstaller --onefile SihotResImport.spec
rem NOT WORKING: c:\Python34\Scripts\pyinstaller --onefile --resource SihotResImport.kv SihotResImport.py
c:\Python34\Scripts\pyinstaller --onefile SihotResImport.spec
c:\Python34\Scripts\pyinstaller --onefile SihotResSync.py
c:\Python34\Scripts\pyinstaller --onefile TestConnectivity.py
c:\Python34\Scripts\pyinstaller --onefile WatchPupPy.py
rem c:\Python34\Scripts\pyinstaller --onefile WebResTester.py
