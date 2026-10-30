"""Validate macOS browser/driver binaries before starting a cloud session."""
import os
import platform
import re
import struct
import subprocess

ARM64 = 0x0100000C


def macho_architectures(path):
    with open(path, 'rb') as stream:
        magic = stream.read(4)
        thin = {b'\xcf\xfa\xed\xfe': '<', b'\xfe\xed\xfa\xcf': '>',
                b'\xce\xfa\xed\xfe': '<', b'\xfe\xed\xfa\xce': '>'}
        fat = {b'\xca\xfe\xba\xbe': ('>', 20), b'\xbe\xba\xfe\xca': ('<', 20),
               b'\xca\xfe\xba\xbf': ('>', 32), b'\xbf\xba\xfe\xca': ('<', 32)}
        if magic in thin:
            data = stream.read(4)
            if len(data) != 4:
                raise ValueError('Mach-O 文件头不完整')
            return {struct.unpack(thin[magic] + 'I', data)[0]}
        if magic in fat:
            endian, entry_size = fat[magic]
            raw_count = stream.read(4)
            if len(raw_count) != 4:
                raise ValueError('Mach-O 通用二进制文件头不完整')
            count = struct.unpack(endian + 'I', raw_count)[0]
            if not 0 < count <= 64:
                raise ValueError('Mach-O 架构数量无效')
            architectures = set()
            for _ in range(count):
                entry = stream.read(entry_size)
                if len(entry) != entry_size:
                    raise ValueError('Mach-O 架构表不完整')
                architectures.add(struct.unpack(endian + 'I', entry[:4])[0])
            return architectures
    raise ValueError('不是可识别的 Mach-O 可执行文件')


def _major_version(path):
    result = subprocess.run([path, '--version'], check=True, capture_output=True,
                            text=True, timeout=10)
    match = re.search(r'\b(\d+)\.\d+\.\d+\.\d+\b', result.stdout + result.stderr)
    if not match:
        raise RuntimeError(f'无法读取版本：{path}')
    return int(match.group(1))


def validate_browser_pair(browser, driver):
    if platform.machine().lower() not in ('arm64', 'aarch64'):
        raise RuntimeError('当前进程不是 Apple Silicon 原生 ARM64，无法启动此版本')
    for name, path in (('浏览器', browser), ('浏览器驱动', driver)):
        if not os.path.isfile(path):
            raise RuntimeError(f'{name}不存在：{path}')
        try:
            architectures = macho_architectures(path)
        except (OSError, ValueError) as exc:
            raise RuntimeError(f'无法验证{name}架构：{exc}') from exc
        if ARM64 not in architectures:
            raise RuntimeError(f'{name}不包含 ARM64 架构：{path}')
    try:
        browser_major = _major_version(browser)
        driver_major = _major_version(driver)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f'无法读取浏览器或驱动版本：{exc}') from exc
    if browser_major != driver_major:
        raise RuntimeError(f'浏览器与驱动主版本不匹配：{browser_major} / {driver_major}')
