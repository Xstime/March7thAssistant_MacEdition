import struct
from unittest.mock import patch

import pytest

from utils.macos_browser import ARM64, macho_architectures, validate_browser_pair


def test_reads_thin_and_universal_macho_headers(tmp_path):
    thin = tmp_path / 'thin'
    thin.write_bytes(b'\xcf\xfa\xed\xfe' + struct.pack('<I', ARM64))
    assert macho_architectures(thin) == {ARM64}
    universal = tmp_path / 'universal'
    universal.write_bytes(b'\xca\xfe\xba\xbe' + struct.pack('>I', 2) +
                          struct.pack('>IIIII', 0x01000007, 0, 0, 0, 0) +
                          struct.pack('>IIIII', ARM64, 0, 0, 0, 0))
    assert macho_architectures(universal) == {0x01000007, ARM64}


def test_rejects_non_arm64_or_mismatched_version(tmp_path):
    browser, driver = tmp_path / 'browser', tmp_path / 'driver'
    browser.write_bytes(b'\xcf\xfa\xed\xfe' + struct.pack('<I', ARM64))
    driver.write_bytes(b'\xcf\xfa\xed\xfe' + struct.pack('<I', 0x01000007))
    with patch('utils.macos_browser.platform.machine', return_value='arm64'):
        with pytest.raises(RuntimeError, match='ARM64'):
            validate_browser_pair(str(browser), str(driver))
        driver.write_bytes(browser.read_bytes())
        with patch('utils.macos_browser._major_version', side_effect=[140, 141]):
            with pytest.raises(RuntimeError, match='不匹配'):
                validate_browser_pair(str(browser), str(driver))
