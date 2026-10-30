# Build with the arm64 Python environment described in docs/macos-development.md.
from pathlib import Path
from importlib import metadata
import selenium
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

selenium_root = Path(selenium.__file__).parent
manager = selenium_root / 'webdriver' / 'common' / 'macos' / 'selenium-manager'
datas = [('assets', 'assets'), ('LICENSE', '.')] + collect_data_files('rapidocr')
# Include the installed distributions' license files when present. Distribution
# metadata can have multiple files with the same name, so keep package folders.
for dist in metadata.distributions():
    package = dist.metadata.get('Name', 'unknown').replace('/', '_')
    for item in dist.files or ():
        parts = Path(str(item)).parts
        if not any(part.endswith('.dist-info') for part in parts):
            continue
        if not any('license' in part.lower() or 'copying' in part.lower() for part in parts):
            continue
        source = Path(dist.locate_file(item))
        if source.is_file():
            info_index = next(i for i, part in enumerate(parts) if part.endswith('.dist-info'))
            relative_parent = Path(*parts[info_index + 1:-1])
            datas.append((str(source), str(Path('licenses') / package / relative_parent)))
binaries = [(str(manager), 'selenium/webdriver/common/macos')]
binaries += collect_dynamic_libs('onnxruntime')
binaries += [item for item in collect_dynamic_libs('openvino')
             if not Path(item[0]).name.startswith(('libtbbbind_', 'libhwloc', 'libtbbmalloc'))]

a = Analysis(
    ['app.py'], pathex=[], binaries=binaries, datas=datas,
    hiddenimports=['main', 'selenium.webdriver.chrome.webdriver',
                   'selenium.webdriver.edge.webdriver'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6'], noarchive=False,
)
# Optional TBB binding and allocator helpers cannot be rewritten by Apple's
# install_name_tool. The CPU plugin has no direct dependency on them.
a.binaries = [item for item in a.binaries
              if not Path(item[0]).name.startswith(('libtbbbind_', 'libhwloc', 'libtbbmalloc'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='March7thAssistant', console=False, target_arch='arm64',
          codesign_identity='-', argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name='March7thAssistant',
               strip=False, upx=False)
app = BUNDLE(coll, name='March7thAssistant.app',
             bundle_identifier='org.march7thassistant.macos',
             info_plist={'NSHighResolutionCapable': True,
                         'LSMinimumSystemVersion': '14.0'})
