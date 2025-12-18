import serial
import serial.tools.list_ports
import logging
import re
import sys

logger = logging.getLogger(__name__)

FTDI_VID = 0x0403

def _is_ftdi_like(p) -> bool:
    # Strong: VID
    vid = getattr(p, "vid", None)
    if vid == FTDI_VID:
        return True

    # Next: HWID often contains VID_0403 on Windows
    hwid = (getattr(p, "hwid", "") or "").upper()
    if "VID_0403" in hwid or "VID:PID=0403" in hwid or "0403:" in hwid:
        return True

    # Weak: strings (keep as last resort)
    mfg  = (getattr(p, "manufacturer", "") or "").upper()
    desc = (getattr(p, "description", "") or "").upper()
    return ("FTDI" in mfg) or ("FTDI" in desc)

def getallports(ftdi_only=True):
    allports = list(serial.tools.list_ports.comports())

    if not allports:
        return []

    if ftdi_only:
        cand = [p for p in allports if _is_ftdi_like(p)]
        # If detection fails (common on some Windows setups), fall back to *all* ports
        return cand if cand else allports

    return allports

def getallportssn():
    allports = getallports()

    portssn = []
    for port in allports:
        portssn.append(port.serial_number)
    return portssn

def getallportsastext():
    allports = getallports()
    portsastext = []
    for port in allports:
        portsastext.append([port.serial_number, port.device])
    return portsastext

def getportbyserialnumber(sn):
    allports = getallports()
    for port in allports:
        if port.serial_number == sn:
            return port
    return None

def getdevicebyserialnumber(sn):
    port = getportbyserialnumber(sn)
    return port.device if port else None


_warned_legacy_numeric = False

def connectdevice(sn=None, port_str=None):
    global _warned_legacy_numeric

    # If UI accidentally passes legacy "100/101/..." ignore it (warn once)
    if isinstance(port_str, str) and port_str.strip().isdigit():
        if not _warned_legacy_numeric:
            logger.warning(f"👆 Ignoring legacy numeric port_str={port_str}")
            _warned_legacy_numeric = True
        port_str = None

    # 1) If UI passed an explicit port (COM7), use it
    if port_str:
        nanoport = port_str

    # 2) Else, if sn provided, resolve by serial number
    elif sn is not None:
        nanoport = getdevicebyserialnumber(sn)

    # 3) Else, pick the first candidate
    else:
        ports = getallports(ftdi_only=True)
        if not ports:
            ports = getallports(ftdi_only=False)  # fallback
        nanoport = ports[0].device if ports else None

    if not nanoport:
        logger.warning("👆 No serial port device found")
        return None   # don't sys.exit inside a GUI app

    try:
        tty = serial.Serial(
            nanoport,
            baudrate=600000,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=0.01
        )
        return tty
    except Exception as e:
        logger.error(f"❌ Failed to open serial port {nanoport}: {e}")
        return None

def send_command(command):
    shproto.dispatcher.process_03(command)
    logger.info(f'   ✅ Send command {command} ')
    return