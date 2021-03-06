# -*- mode: python -*-
from kivy.deps import sdl2, glew

block_cipher = None

a = Analysis(['AcuSihotMonitor.py'],
             pathex=['C:\\src\\python\\AcuSihotInterfaces'],
             binaries=[],
             datas=[ ('AcuSihotMonitor.kv', '.') ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
          name='AcuSihotMonitor',
          debug=False,
          strip=False,
          upx=False,
          console=True   # has to be True because print statements need a console window
         )
