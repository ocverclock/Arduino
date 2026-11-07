#!/usr/bin/env python3
"""MK2 v0.4.2 : fusion application autonomous_power + Optiboot 16 MHz.

Depuis Mk2_fasterControl_Full :
  python3 /chemin/fusion_mk2_v0.4.2_power_optiboot.py

Ne programme aucun microcontrôleur : construit et contrôle uniquement un fichier HEX.
"""
from pathlib import Path
import hashlib
import sys

BOOT_NAME = 'optiboot_atmega328_16MHz_115200_ArduinoCore-avr_1.8.6.hex'
OUTPUT = 'MK2_v0.4.2_POWER_OPTIBOOT.hex'


def decode_hex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    base = 0
    eof = False
    for ln, line in enumerate(path.read_text(encoding='ascii').splitlines(), 1):
        if not line or not line.startswith(':'):
            raise ValueError(f'{path.name}:{ln}: ligne HEX invalide')
        try:
            packet = bytes.fromhex(line[1:])
        except ValueError as exc:
            raise ValueError(f'{path.name}:{ln}: caractères HEX invalides') from exc
        if len(packet) < 5 or len(packet) != packet[0] + 5 or sum(packet) % 256:
            raise ValueError(f'{path.name}:{ln}: taille/checksum incorrect')
        count, address, kind = packet[0], int.from_bytes(packet[1:3], 'big'), packet[3]
        data = packet[4:4 + count]
        if eof:
            raise ValueError(f'{path.name}:{ln}: données après EOF')
        if kind == 0:
            for offset, byte in enumerate(data):
                a = base + address + offset
                if a >= 0x8000:
                    raise ValueError(f'Adresse hors Flash ATmega328P : 0x{a:05X}')
                if a in memory and memory[a] != byte:
                    raise ValueError(f'Données contradictoires à 0x{a:04X}')
                memory[a] = byte
        elif kind == 1:
            if count:
                raise ValueError('Enregistrement EOF non vide')
            eof = True
        elif kind == 2:
            if count != 2:
                raise ValueError('Adresse segment incorrecte')
            base = int.from_bytes(data, 'big') << 4
        elif kind == 4:
            if count != 2:
                raise ValueError('Adresse linéaire incorrecte')
            base = int.from_bytes(data, 'big') << 16
        elif kind not in (3, 5):
            raise ValueError(f'Type Intel HEX non pris en charge : {kind}')
    if not eof or not memory:
        raise ValueError(f'{path.name}: EOF absent ou programme vide')
    return memory


def hex_record(addr: int, data: bytes) -> str:
    body = bytes((len(data), addr >> 8, addr & 0xFF, 0)) + data
    return ':' + (body + bytes((-sum(body) & 255,))).hex().upper()


def main() -> int:
    project = Path.cwd()
    app_file = project / '.pio/build/autonomous_power/firmware.hex'
    boot_file = project.parent.parent / 'BOOTLOADER_OPTIBOOT' / BOOT_NAME
    ini = project / 'platformio.ini'
    uart = project / 'mk2_uart.cpp'
    for name, path in (('PlatformIO', ini), ('UART v0.4.2', uart),
                       ('Application POWER', app_file), ('Optiboot', boot_file)):
        if not path.is_file():
            raise ValueError(f'{name} introuvable : {path}')
    ini_text = ini.read_text(encoding='utf-8')
    if 'v0.4.2' not in ini_text or '-DMK2_ALLOW_TRIAC_OUTPUT=1' not in ini_text:
        raise ValueError('Mauvais projet : v0.4.2 autonomous_power attendu')
    if 'MK2_PV_ROUTER_V0_4_2' not in uart.read_text(encoding='utf-8'):
        raise ValueError('Mauvaise version UART : v0.4.2 attendue')
    if app_file.stat().st_mtime + 1 < ini.stat().st_mtime:
        raise ValueError('firmware.hex plus ancien que platformio.ini : relancer le Build autonomous_power')

    app = decode_hex(app_file)
    boot = decode_hex(boot_file)
    if min(app) != 0 or max(app) >= 0x7E00:
        raise ValueError(f'Application incompatible Optiboot : 0x{min(app):04X}..0x{max(app):04X}')
    if min(boot) < 0x7E00 or max(boot) != 0x7FFF:
        raise ValueError(f'Optiboot invalide : 0x{min(boot):04X}..0x{max(boot):04X}')
    overlap = app.keys() & boot.keys()
    if overlap:
        raise ValueError(f'Chevauchement mémoire à 0x{min(overlap):04X}')

    merged = app | boot
    lines = []
    for addr in range(0, 0x8000, 16):
        if any((addr + offset) in merged for offset in range(16)):
            chunk = bytes(merged.get(addr + offset, 0xFF) for offset in range(16))
            lines.append(hex_record(addr, chunk))
    lines.append(':00000001FF')
    target = project / OUTPUT
    target.write_text('\n'.join(lines) + '\n', encoding='ascii')

    readback = decode_hex(target)
    if any(readback[a] != v for a, v in merged.items()):
        target.unlink(missing_ok=True)
        raise ValueError('Vérification du fichier fusionné échouée')
    print('SUCCESS :', target)
    print('Application autonomous_power :', len(app), 'octets HEX, adresse maximale', hex(max(app)))
    print('Optiboot :', len(boot), 'octets HEX, emplacement', hex(min(boot)), 'à', hex(max(boot)))
    print('Contrôle de chaque octet et des checksums : OK')
    print('SHA-256 :', hashlib.sha256(target.read_bytes()).hexdigest())
    print('ATTENTION : ce script ne programme pas l’ATmega ; utiliser AVRDUDE séparément.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print('ERREUR :', error, file=sys.stderr)
        sys.exit(1)
