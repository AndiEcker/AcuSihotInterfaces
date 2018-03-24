set PATH=C:\Python35\;C:\Python35\Scripts;%PATH%

rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile --resource AcuSihotMonitor.kv AcuSihotMonitor.py
c:\Python35\Scripts\pyinstaller --onefile AcuServer.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue AcuSihotMonitor.spec
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue AssCacheSync.spec
c:\Python35\Scripts\pyinstaller --onefile AssServer.py
c:\Python35\Scripts\pyinstaller --onefile ClientQuestionnaireExport.py
rem c:\Python35\Scripts\pyinstaller --onefile KernelGuestTester.py
rem c:\Python35\Scripts\pyinstaller --onefile MatchcodeToObjId.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue ShSfClientMigration.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue SfClientValidator.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue SihotMigration.py
c:\Python35\Scripts\pyinstaller --onefile SihotOccLogChecker.py
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile --resource SihotResImport.kv SihotResImport.py
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile SihotResImport.spec
rem NOT WORKING: c:\Python35\Scripts\pyinstaller --onefile --resource SihotResImport.kv SihotResImport.py
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue SihotResImport.spec
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue SihotResImport_console.spec
c:\Python35\Scripts\pyinstaller --onefile --hiddenimport queue SihotResSync.py
c:\Python35\Scripts\pyinstaller --onefile TestConnectivity.py
c:\Python35\Scripts\pyinstaller --onefile WatchPupPy.py
rem c:\Python35\Scripts\pyinstaller --onefile WebResTester.py
