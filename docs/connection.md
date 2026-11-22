# Connecting to the oscilloscope over USB

How to make Python talk to a TDS 1012C-EDU through its rear USB Device port on Windows.

Tested on: Windows 11, Python 3.11, PyVISA 1.16, NI-VISA 2026 Q4, oscilloscope firmware v25.11.

## 1. Instrument

1. Turn the oscilloscope on.
2. Connect a USB cable from the rear **USB Device** port (square type B connector) to the computer. Plug it directly into the computer, not into a hub, if detection fails.
3. On the front panel: **Utility ► Options ► Rear USB Port ► Computer**. The menu name can differ between firmware versions; check the user manual.

## 2. Python environment

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Check what is already installed

See how Windows enumerated the instrument. Tektronix uses USB vendor ID `0x0699`; the TDS 1012C-EDU reports product ID `0x03AC`.

```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "*VID_0699*" }
```

- Without a VISA driver, the device shows as "Tektronix TDS1012C-EDU" with status `Error` and no class.
- With a working driver, it shows as "USB Test and Measurement Device (IVI)", class `USBTestAndMeasurementDevice`, status `OK`.

Check whether a VISA library is present:

```
pyvisa-info
```

Under `Backends`, `ivi` with `Binary library: Not found` means no VISA library is installed.

## 4. Install a VISA backend

Order of preference:

1. **A VISA library is already installed** (NI-VISA, Keysight IO Libraries, Tektronix TekVISA): use it.
2. **No VISA library:** install NI-VISA from the National Instruments website (`ni.com`, NI-VISA download page). The download page asks you to log in with an NI account. The online installer uses NI Package Manager.
   - On the "Additional items you may wish to install" page, **Deselect All** is enough. The core NI-VISA runtime is installed anyway; the optional items (NI MAX configuration support, Interactive Control, I/O Trace, .NET support, C examples, Driver Development Wizard, PXI Platform Services, NI Certificates Installer) are not needed for this project.
   - The installer also adds NI Package Manager, NI Update Service and the .NET Desktop Runtime, which NI Package Manager needs.
   - The installer recommends disabling Windows Fast Startup, because it can stop USB instruments from being detected after boot.
   - Restart Windows when the installer asks. Before the restart, the device already uses the new driver, but NI-VISA does not list it.
3. **Only if NI-VISA cannot be installed:** pyvisa-py with libusb. This needs a WinUSB or libusb driver bound to the instrument (for example with Zadig), which replaces the driver above. Selecting the wrong device in Zadig breaks that other device. Not tested in this project.

To remove NI-VISA later: uninstall NI-VISA in NI Package Manager, then remove NI Package Manager in Windows Settings ► Apps. Turn Fast Startup back on in Control Panel ► Power Options if you want it.

## 5. Find and open the resource

```python
import pyvisa

rm = pyvisa.ResourceManager()
print(rm.list_resources("USB?*"))
# ('USB0::0x0699::0x03AC::<SERIAL>::INSTR',)
```

The resource string contains the instrument serial number. Do not commit it.

```python
inst = rm.open_resource("USB0::0x0699::0x03AC::<SERIAL>::INSTR")
inst.timeout = 10000            # ms
inst.read_termination = "\n"
inst.write_termination = "\n"

inst.write("*CLS")
print(inst.query("*IDN?"))      # TEKTRONIX,TDS 1012C-EDU,<SERIAL>,CF:91.1CT FV:v25.11
inst.close()
rm.close()
```

The USB resource accepts one process at a time. Close the connection when you are done.

## Troubleshooting

| Symptom | Check |
|---|---|
| No `VID_0699` device in `Get-PnpDevice -PresentOnly` | Instrument off, cable in the front USB Host port instead of the rear Device port, or a bad cable or hub. |
| Device present, but `list_resources()` has no `USB0::0x0699` entry | Restart Windows after installing NI-VISA. Check that no other program has the instrument open. |
| `VI_ERROR_TMO` on a query | Wrong termination, or a command the instrument does not answer. Send `*CLS` and try `*IDN?`. |
