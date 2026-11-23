# Command map: Tektronix TDS 1012C-EDU

Instrument: TDS 1012C-EDU, firmware v25.11, USB (USBTMC). Run: 2026-11-22.
Manual: *Digital Oscilloscope Series Programmer Manual*, Tektronix 077044403. Raw data: [scpi_map.json](scpi_map.json); manual headers: [manual-commands.json](manual-commands.json).

## How the map was made

- 345 headers from the manual: every index entry in Command Descriptions, the `WFMPre:<wfm>:*` headings the index leaves out, and the six headers of Table 2-36.
- For each header with a query form, only the query was sent (`...?`), followed by `*ESR?` and `ALLEv?`. 100 ms between commands, 3 s timeout, device clear after a timeout. Constructed mnemonics were sent with one value: `CH1`, `REFA`, `MEAS1`, `POSITION1`, `HPOS1`, `TP1`, `BATTERY1`; `<wfm>` as `CH1`.
- Response headers on: `HEADer ON`, `VERBose ON`.
- **Accepted** means: a reply within 3 s and no error event (codes 100-399, 404, 410, 420, 430, 440; four-digit codes such as 2244 count by their class, 224). Warnings (5xx) do not count as errors.
- `SET?` and `*LRN?` take about 5 s to arrive, so they were sent with a 30 s timeout. They are listed as accepted with the time marked (`accepted_slow`).
- After a timeout the VISA session was closed and opened again before reading the status. On this instrument the USBTMC device clear stopped working after a long run of unanswered queries.
- Not sent: commands without a query form, `CURVe?`, `WAVFrm?`, `HARDCopy?`, and everything in the blocklist (`*CAL?`, `*TST?`, `SAVe:`, `RECAll:`, `*SAV`, `*RCL`, ...).
- The serial number is replaced with `<SERIAL>` in every recorded reply.

| Result | Count |
|---|---|
| accepted | 177 |
| no_response | 122 |
| no_query_form | 39 |
| excluded | 5 |
| accepted_slow | 2 |

## (a) Documented for this model and accepted (172)

| Header | Query sent | Reply |
|---|---|---|
| `ACQuire?` | `ACQuire?` | :ACQUIRE:MODE SAMPLE;NUMAVG 16;STATE 1;STOPAFTER RUNSTOP |
| `ACQuire:MODe` | `ACQuire:MODe?` | :ACQUIRE:MODE SAMPLE |
| `ACQuire:NUMACq?` | `ACQuire:NUMACq?` | :ACQUIRE:NUMACQ 229100 |
| `ACQuire:NUMAVg` | `ACQuire:NUMAVg?` | :ACQUIRE:NUMAVG 16 |
| `ACQuire:STATE` | `ACQuire:STATE?` | :ACQUIRE:STATE 1 |
| `ACQuire:STOPAfter` | `ACQuire:STOPAfter?` | :ACQUIRE:STOPAFTER RUNSTOP |
| `ALLEv?` | `ALLEv?` | :ALLEV 0,"No events to report - queue empty" |
| `AUTORange:SETTings` | `AUTORange:SETTings?` | :AUTORANGE:SETTINGS BOTH |
| `AUTORange:STATE` | `AUTORange:STATE?` | :AUTORANGE:STATE 0 |
| `AUTOSet:SIGNAL?` | `AUTOSet:SIGNAL?` | :AUTOSET:SIGNAL NONE |
| `BUSY?` | `BUSY?` | :BUSY 0 |
| `CALibrate:STATUS?` | `CALibrate:STATUS?` | :CALIBRATE:STATUS PASS |
| `CH<x>?` | `CH1?` | :CH1:PROBE 1.0E1;CURRENTPROBE 1.0E1;SCALE 2.0E0;POSITION 0.0E0;COUPLI… |
| `CH<x>:BANdwidth` | `CH1:BANdwidth?` | :CH1:BANDWIDTH OFF |
| `CH<x>:COUPling` | `CH1:COUPling?` | :CH1:COUPLING DC |
| `CH<x>:CURRENTPRObe` | `CH1:CURRENTPRObe?` | :CH1:CURRENTPROBE 1.0E1 |
| `CH<x>:INVert` | `CH1:INVert?` | :CH1:INVERT OFF |
| `CH<x>:POSition` | `CH1:POSition?` | :CH1:POSITION 0.0E0 |
| `CH<x>:PRObe` | `CH1:PRObe?` | :CH1:PROBE 1.0E1 |
| `CH<x>:SCAle` | `CH1:SCAle?` | :CH1:SCALE 2.0E0 |
| `CH<x>:VOLts` | `CH1:VOLts?` | :CH1:VOLTS 2.0E0 |
| `CH<x>:YUNit` | `CH1:YUNit?` | :CH1:YUNIT "V" |
| `CURSor?` | `CURSor?` | :CURSOR:FUNCTION OFF;SELECT:SOURCE CH1;:CURSOR:VBARS:UNITS SECONDS;PO… |
| `CURSor:FUNCtion` | `CURSor:FUNCtion?` | :CURSOR:FUNCTION OFF |
| `CURSor:HBArs?` | `CURSor:HBArs?` | :CURSOR:HBARS:UNITS VOLTS;POSITION1 6.4E0;POSITION2 -6.4E0 |
| `CURSor:HBArs:DELTa?` | `CURSor:HBArs:DELTa?` | :CURSOR:HBARS:DELTA 1.28E1 |
| `CURSor:HBArs:POSITION<x>` | `CURSor:HBArs:POSITION1?` | :CURSOR:HBARS:POSITION1 6.4E0 |
| `CURSor:HBArs:UNIts?` | `CURSor:HBArs:UNIts?` | :CURSOR:HBARS:UNITS VOLTS |
| `CURSor:SELect:SOUrce` | `CURSor:SELect:SOUrce?` | :CURSOR:SELECT:SOURCE CH1 |
| `CURSor:VBArs?` | `CURSor:VBArs?` | :CURSOR:VBARS:UNITS SECONDS;POSITION1 -7.8E-4;POSITION2 5.0E-4 |
| `CURSor:VBArs:DELTa?` | `CURSor:VBArs:DELTa?` | :CURSOR:VBARS:DELTA 1.28E-3 |
| `CURSor:VBArs:HDELTa?` | `CURSor:VBArs:HDELTa?` | :CURSOR:VBARS:HDELTA 1.28E-3 |
| `CURSor:VBArs:HPOS<x>?` | `CURSor:VBArs:HPOS1?` | :CURSOR:VBARS:HPOS1 9.9E37 |
| `CURSor:VBArs:POSITION<x>` | `CURSor:VBArs:POSITION1?` | :CURSOR:VBARS:POSITION1 -7.8E-4 |
| `CURSor:VBArs:UNIts` | `CURSor:VBArs:UNIts?` | :CURSOR:VBARS:UNITS SECONDS |
| `CURSor:VBArs:VDELTa?` | `CURSor:VBArs:VDELTa?` | :CURSOR:VBARS:VDELTA 9.9E37 |
| `DATa` | `DATa?` | :DATA:ENCDG RIBINARY;DESTINATION REFA;SOURCE CH2;START 1;STOP 2500;WI… |
| `DATa:DESTination` | `DATa:DESTination?` | :DATA:DESTINATION REFA |
| `DATa:ENCdg` | `DATa:ENCdg?` | :DATA:ENCDG RIBINARY |
| `DATa:SOUrce` | `DATa:SOUrce?` | :DATA:SOURCE CH2 |
| `DATa:STARt` | `DATa:STARt?` | :DATA:START 1 |
| `DATa:STOP` | `DATa:STOP?` | :DATA:STOP 2500 |
| `DATa:TARget` | `DATa:TARget?` | :DATA:TARGET REFA |
| `DATa:WIDth` | `DATa:WIDth?` | :DATA:WIDTH 1 |
| `DATE` | `DATE?` | :DATE "2026-11-22" |
| `*DDT` | `*DDT?` | #10 |
| `DESE` | `DESE?` | :DESE 255 |
| `DIAg:RESUlt:FLAg?` | `DIAg:RESUlt:FLAg?` | :DIAG:RESULT:FLAG PASS |
| `DIAg:RESUlt:LOG?` | `DIAg:RESUlt:LOG?` | :DIAG:RESULT:LOG "pass--CPU,pass--ACQ1,pass--EXTENSION," |
| `DISplay?` | `DISplay?` | :DISPLAY:FORMAT YT;STYLE VECTORS;PERSISTENCE 0;CONTRAST 50;INVERT OFF |
| `DISplay:CONTRast` | `DISplay:CONTRast?` | :DISPLAY:CONTRAST 50 |
| `DISplay:FORMat` | `DISplay:FORMat?` | :DISPLAY:FORMAT YT |
| `DISplay:INVert` | `DISplay:INVert?` | :DISPLAY:INVERT OFF |
| `DISplay:PERSistence` | `DISplay:PERSistence?` | :DISPLAY:PERSISTENCE 0 |
| `DISplay:STYle` | `DISplay:STYle?` | :DISPLAY:STYLE VECTORS |
| `ERRLOG:FIRST?` | `ERRLOG:FIRST?` | :ERRLOG:FIRST "" |
| `ERRLOG:NEXT?` | `ERRLOG:NEXT?` | :ERRLOG:NEXT "" |
| `*ESE` | `*ESE?` | 0 |
| `*ESR?` | `*ESR?` | 0 |
| `EVENT?` | `EVENT?` | :EVENT 0 |
| `EVMsg?` | `EVMsg?` | :EVMSG 0,"No events to report - queue empty" |
| `EVQty?` | `EVQty?` | :EVQTY 0 |
| `FILESystem?` | `FILESystem?` | :FILESYSTEM:CWD "";FREESPACE 0 |
| `FILESystem:CWD` | `FILESystem:CWD?` | :FILESYSTEM:CWD "" |
| `FILESystem:DIR?` | `FILESystem:DIR?` | :FILESYSTEM:DIR |
| `FILESystem:FREESpace?` | `FILESystem:FREESpace?` | :FILESYSTEM:FREESPACE 0 |
| `HARDCopy:BUTTON` | `HARDCopy:BUTTON?` | :HARDCOPY:BUTTON SAVESIMAGE |
| `HARDCopy:FORMat` | `HARDCopy:FORMat?` | :HARDCOPY:FORMAT JPEG |
| `HARDCopy:INKSaver` | `HARDCopy:INKSaver?` | :HARDCOPY:INKSAVER OFF |
| `HARDCopy:LAYout` | `HARDCopy:LAYout?` | :HARDCOPY:LAYOUT PORTRAIT |
| `HARDCopy:PORT` | `HARDCopy:PORT?` | :HARDCOPY:PORT USB |
| `HDR` | `HDR?` | :HDR 1 |
| `HEADer` | `HEADer?` | :HEADER 1 |
| `HORizontal?` | `HORizontal?` | :HORIZONTAL:VIEW MAIN;RECORDLENGTH 2500;MAIN:SCALE 5.0E-4;POSITION 0.… |
| `HORizontal:DELay?` | `HORizontal:DELay?` | :HORIZONTAL:DELAY:SCALE 5.0E-9;POSITION 0.0E0 |
| `HORizontal:DELay:POSition` | `HORizontal:DELay:POSition?` | :HORIZONTAL:DELAY:POSITION 0.0E0 |
| `HORizontal:DELay:SCAle` | `HORizontal:DELay:SCAle?` | :HORIZONTAL:DELAY:SCALE 5.0E-9 |
| `HORizontal:DELay:SECdiv` | `HORizontal:DELay:SECdiv?` | :HORIZONTAL:DELAY:SECDIV 5.0E-9 |
| `HORizontal:MAIn?` | `HORizontal:MAIn?` | :HORIZONTAL:MAIN:SCALE 5.0E-4;POSITION 0.0E0 |
| `HORizontal:MAIn:POSition` | `HORizontal:MAIn:POSition?` | :HORIZONTAL:MAIN:POSITION 0.0E0 |
| `HORizontal:MAIn:SCAle` | `HORizontal:MAIn:SCAle?` | :HORIZONTAL:MAIN:SCALE 5.0E-4 |
| `HORizontal:MAIn:SECdiv` | `HORizontal:MAIn:SECdiv?` | :HORIZONTAL:MAIN:SECDIV 5.0E-4 |
| `HORizontal:POSition` | `HORizontal:POSition?` | :HORIZONTAL:POSITION 0.0E0 |
| `HORizontal:RECOrdlength?` | `HORizontal:RECOrdlength?` | :HORIZONTAL:RECORDLENGTH 2500 |
| `HORizontal:SCAle` | `HORizontal:SCAle?` | :HORIZONTAL:SCALE 5.0E-4 |
| `HORizontal:SECdiv` | `HORizontal:SECdiv?` | :HORIZONTAL:SECDIV 5.0E-4 |
| `HORizontal:VIEW` | `HORizontal:VIEW?` | :HORIZONTAL:VIEW MAIN |
| `ID?` | `ID?` | ID TEK/TDS 1012C-EDU,CF:91.1CT FV:v25.11 |
| `*IDN?` | `*IDN?` | TEKTRONIX,TDS 1012C-EDU,<SERIAL>,CF:91.1CT FV:v25.11 |
| `LANGuage` | `LANGuage?` | :LANGUAGE PORTUGUESE |
| `LOCk` | `LOCk?` | :LOCK NONE |
| `*LRN?` | `*LRN?` | :HEADER 1;:VERBOSE 1;:DATA:ENCDG RIBINARY;DESTINATION REFA;SOURCE CH2… *(4.89 s)* |
| `MATH?` | `MATH?` | :MATH:DEFINE "CH1 - CH2";VERTICAL:POSITION 0.0E0;SCALE 2.0E0;:MATH:FF… |
| `MATH:DEFINE` | `MATH:DEFINE?` | :MATH:DEFINE "CH1 - CH2" |
| `MATH:FFT?` | `MATH:FFT?` | :MATH:FFT:HORIZONTAL:POSITION 5.0E1;SCALE 1.0E0;:MATH:FFT:VERTICAL:PO… |
| `MATH:FFT:HORizontal:POSition` | `MATH:FFT:HORizontal:POSition?` | :MATH:FFT:HORIZONTAL:POSITION 5.0E1 |
| `MATH:FFT:HORizontal:SCAle` | `MATH:FFT:HORizontal:SCAle?` | :MATH:FFT:HORIZONTAL:SCALE 1.0E0 |
| `MATH:FFT:VERtical:POSition` | `MATH:FFT:VERtical:POSition?` | :MATH:FFT:VERTICAL:POSITION 0.0E0 |
| `MATH:FFT:VERtical:SCAle` | `MATH:FFT:VERtical:SCAle?` | :MATH:FFT:VERTICAL:SCALE 1.0E0 |
| `MATH:VERtical?` | `MATH:VERtical?` | :MATH:VERTICAL:POSITION 0.0E0;SCALE 2.0E0 |
| `MATH:VERtical:POSition` | `MATH:VERtical:POSition?` | :MATH:VERTICAL:POSITION 0.0E0 |
| `MATH:VERtical:SCAle` | `MATH:VERtical:SCAle?` | :MATH:VERTICAL:SCALE 2.0E0 |
| `MEASUrement?` | `MEASUrement?` | :MEASUREMENT:MEAS1:TYPE FREQUENCY;UNITS "Hz";SOURCE CH1;:MEASUREMENT:… |
| `MEASUrement:IMMed?` | `MEASUrement:IMMed?` | :MEASUREMENT:IMMED:TYPE PERIOD;UNITS "s";SOURCE1 CH1 |
| `MEASUrement:IMMed:SOUrce[1]` | `MEASUrement:IMMed:SOUrce?` | :MEASUREMENT:IMMED:SOURCE CH1 |
| `MEASUrement:IMMed:TYPe` | `MEASUrement:IMMed:TYPe?` | :MEASUREMENT:IMMED:TYPE PERIOD |
| `MEASUrement:IMMed:UNIts?` | `MEASUrement:IMMed:UNIts?` | :MEASUREMENT:IMMED:UNITS "s" |
| `MEASUrement:IMMed:VALue?` | `MEASUrement:IMMed:VALue?` | :MEASUREMENT:IMMED:VALUE 1.0E-3 |
| `MEASUrement:MEAS<x>?` | `MEASUrement:MEAS1?` | :MEASUREMENT:MEAS1:TYPE FREQUENCY;UNITS "Hz";SOURCE CH1 |
| `MEASUrement:MEAS<x>:SOUrce` | `MEASUrement:MEAS1:SOUrce?` | :MEASUREMENT:MEAS1:SOURCE CH1 |
| `MEASUrement:MEAS<x>:SOUrce2` | `MEASUrement:MEAS1:SOUrce2?` | :MEASUREMENT:MEAS1:SOURCE2 CH1 |
| `MEASUrement:MEAS<x>:TYPe` | `MEASUrement:MEAS1:TYPe?` | :MEASUREMENT:MEAS1:TYPE FREQUENCY |
| `MEASUrement:MEAS<x>:UNIts?` | `MEASUrement:MEAS1:UNIts?` | :MEASUREMENT:MEAS1:UNITS "Hz" |
| `MEASUrement:MEAS<x>:VALue?` | `MEASUrement:MEAS1:VALue?` | :MEASUREMENT:MEAS1:VALUE 9.999999389648E2 |
| `*OPC` | `*OPC?` | 1 |
| `PICTBridge:DATEPRINT` | `PICTBridge:DATEPRINT?` | :PICTBRIDGE:DATEPRINT DEFLT |
| `PICTBridge:IDPRINT` | `PICTBridge:IDPRINT?` | :PICTBRIDGE:IDPRINT DEFLT |
| `PICTBridge:IMAGESIZE` | `PICTBridge:IMAGESIZE?` | :PICTBRIDGE:IMAGESIZE DEFLT |
| `PICTBridge:PAPERSIZE` | `PICTBridge:PAPERSIZE?` | :PICTBRIDGE:PAPERSIZE DEFLT |
| `PICTBridge:PAPERTYPE` | `PICTBridge:PAPERTYPE?` | :PICTBRIDGE:PAPERTYPE DEFLT |
| `PICTBridge:PRINTQUAL` | `PICTBridge:PRINTQUAL?` | :PICTBRIDGE:PRINTQUAL DEFLT |
| `*PSC` | `*PSC?` | 1 |
| `SELect?` | `SELect?` | :SELECT:CH1 1;CH2 0;MATH 0;REFA 0;REFB 0 |
| `SELect:<wfm>` | `SELect:CH1?` | :SELECT:CH1 1 |
| `SET?` | `SET?` | :HEADER 1;:VERBOSE 1;:DATA:ENCDG RIBINARY;DESTINATION REFA;SOURCE CH2… *(4.906 s)* |
| `*SRE` | `*SRE?` | 0 |
| `*STB?` | `*STB?` | 0 |
| `TIMe` | `TIMe?` | :TIME "20:22:00" |
| `TRIGger` | `TRIGger?` | :TRIGGER:MAIN:MODE AUTO;TYPE EDGE;HOLDOFF:VALUE 5.0E-7;:TRIGGER:MAIN:… |
| `TRIGger:MAIn` | `TRIGger:MAIn?` | :TRIGGER:MAIN:MODE AUTO;TYPE EDGE;HOLDOFF:VALUE 5.0E-7;:TRIGGER:MAIN:… |
| `TRIGger:MAIn:EDGE?` | `TRIGger:MAIn:EDGE?` | :TRIGGER:MAIN:EDGE:SOURCE CH1;COUPLING DC;SLOPE RISE |
| `TRIGger:MAIn:EDGE:COUPling` | `TRIGger:MAIn:EDGE:COUPling?` | :TRIGGER:MAIN:EDGE:COUPLING DC |
| `TRIGger:MAIn:EDGE:SLOpe` | `TRIGger:MAIn:EDGE:SLOpe?` | :TRIGGER:MAIN:EDGE:SLOPE RISE |
| `TRIGger:MAIn:EDGE:SOUrce` | `TRIGger:MAIn:EDGE:SOUrce?` | :TRIGGER:MAIN:EDGE:SOURCE CH1 |
| `TRIGger:MAIn:FREQuency?` | `TRIGger:MAIn:FREQuency?` | :TRIGGER:MAIN:FREQUENCY 9.99999760869383E2 |
| `TRIGger:MAIn:HOLDOff?` | `TRIGger:MAIn:HOLDOff?` | :TRIGGER:MAIN:HOLDOFF:VALUE 5.0E-7 |
| `TRIGger:MAIn:HOLDOff:VALue` | `TRIGger:MAIn:HOLDOff:VALue?` | :TRIGGER:MAIN:HOLDOFF:VALUE 5.0E-7 |
| `TRIGger:MAIn:LEVel` | `TRIGger:MAIn:LEVel?` | :TRIGGER:MAIN:LEVEL 2.56E0 |
| `TRIGger:MAIn:MODe` | `TRIGger:MAIn:MODe?` | :TRIGGER:MAIN:MODE AUTO |
| `TRIGger:MAIn:PULse?` | `TRIGger:MAIn:PULse?` | :TRIGGER:MAIN:PULSE:SOURCE CH1;WIDTH:POLARITY NEGATIVE;WHEN OUTSIDE;W… |
| `TRIGger:MAIn:PULse:SOUrce` | `TRIGger:MAIn:PULse:SOUrce?` | :TRIGGER:MAIN:PULSE:SOURCE CH1 |
| `TRIGger:MAIn:PULse:WIDth?` | `TRIGger:MAIn:PULse:WIDth?` | :TRIGGER:MAIN:PULSE:WIDTH:POLARITY NEGATIVE;WHEN OUTSIDE;WIDTH 7.5002… |
| `TRIGger:MAIn:PULse:WIDth:POLarity` | `TRIGger:MAIn:PULse:WIDth:POLarity?` | :TRIGGER:MAIN:PULSE:WIDTH:POLARITY NEGATIVE |
| `TRIGger:MAIn:PULse:WIDth:WHEN` | `TRIGger:MAIn:PULse:WIDth:WHEN?` | :TRIGGER:MAIN:PULSE:WIDTH:WHEN OUTSIDE |
| `TRIGger:MAIn:PULse:WIDth:WIDth` | `TRIGger:MAIn:PULse:WIDth:WIDth?` | :TRIGGER:MAIN:PULSE:WIDTH:WIDTH 7.5002E-3 |
| `TRIGger:MAIn:TYPe` | `TRIGger:MAIn:TYPe?` | :TRIGGER:MAIN:TYPE EDGE |
| `TRIGger:MAIn:VIDeo?` | `TRIGger:MAIn:VIDeo?` | :TRIGGER:MAIN:VIDEO:SOURCE CH1;SYNC FIELD;POLARITY NORMAL;LINE 1;STAN… |
| `TRIGger:MAIn:VIDeo:LINE` | `TRIGger:MAIn:VIDeo:LINE?` | :TRIGGER:MAIN:VIDEO:LINE 1 |
| `TRIGger:MAIn:VIDeo:POLarity` | `TRIGger:MAIn:VIDeo:POLarity?` | :TRIGGER:MAIN:VIDEO:POLARITY NORMAL |
| `TRIGger:MAIn:VIDeo:SOUrce` | `TRIGger:MAIn:VIDeo:SOUrce?` | :TRIGGER:MAIN:VIDEO:SOURCE CH1 |
| `TRIGger:MAIn:VIDeo:STANDard` | `TRIGger:MAIn:VIDeo:STANDard?` | :TRIGGER:MAIN:VIDEO:STANDARD NTSC |
| `TRIGger:MAIn:VIDeo:SYNC` | `TRIGger:MAIn:VIDeo:SYNC?` | :TRIGGER:MAIN:VIDEO:SYNC FIELD |
| `TRIGger:STATE?` | `TRIGger:STATE?` | :TRIGGER:STATE TRIGGER |
| `VERBose` | `VERBose?` | :VERBOSE 1 |
| `WFMPre?` | `WFMPre?` | :WFMPRE:BYT_NR 1;BIT_NR 8;ENCDG BIN;BN_FMT RI;BYT_OR MSB |
| `WFMPre:<wfm>?` | `WFMPre:CH1?` | :WFMPRE:CH1:WFID "Ch1, DC coupling, 2.0E0 V/div, 5.0E-4 s/div, 2500 p… |
| `WFMPre:<wfm>:NR_Pt?` | `WFMPre:CH1:NR_Pt?` | :WFMPRE:CH1:NR_PT 2500 |
| `WFMPre:<wfm>:YZEro` | `WFMPre:CH1:YZEro?` | :WFMPRE:CH1:YZERO 0.0E0 |
| `WFMPre:BIT_Nr` | `WFMPre:BIT_Nr?` | :WFMPRE:BIT_NR 8 |
| `WFMPre:BN_Fmt` | `WFMPre:BN_Fmt?` | :WFMPRE:BN_FMT RI |
| `WFMPre:BYT_Nr` | `WFMPre:BYT_Nr?` | :WFMPRE:BYT_NR 1 |
| `WFMPre:BYT_Or` | `WFMPre:BYT_Or?` | :WFMPRE:BYT_OR MSB |
| `WFMPre:ENCdg` | `WFMPre:ENCdg?` | :WFMPRE:ENCDG BIN |
| `WFMPre:<wfm>:PT_Fmt` | `WFMPre:CH1:PT_Fmt?` | :WFMPRE:CH1:PT_FMT Y |
| `WFMPre:<wfm>:PT_Off` | `WFMPre:CH1:PT_Off?` | :WFMPRE:CH1:PT_OFF 0 |
| `WFMPre:<wfm>:WFId?` | `WFMPre:CH1:WFId?` | :WFMPRE:CH1:WFID "Ch1, DC coupling, 2.0E0 V/div, 5.0E-4 s/div, 2500 p… |
| `WFMPre:<wfm>:XINcr` | `WFMPre:CH1:XINcr?` | :WFMPRE:CH1:XINCR 2.0E-6 |
| `WFMPre:<wfm>:XUNit` | `WFMPre:CH1:XUNit?` | :WFMPRE:CH1:XUNIT "s" |
| `WFMPre:<wfm>:XZEro` | `WFMPre:CH1:XZEro?` | :WFMPRE:CH1:XZERO -2.5E-3 |
| `WFMPre:<wfm>:YMUlt` | `WFMPre:CH1:YMUlt?` | :WFMPRE:CH1:YMULT 8.0E-2 |
| `WFMPre:<wfm>:YOFf` | `WFMPre:CH1:YOFf?` | :WFMPRE:CH1:YOFF 0.0E0 |
| `WFMPre:<wfm>:YUNit` | `WFMPre:CH1:YUNit?` | :WFMPRE:CH1:YUNIT "Volts" |

## (b) Documented for other series only, and accepted here (7)

| Header | Query sent | Reply | The manual says |
|---|---|---|---|
| `MEASUrement:IMMed:SOURCE2` | `MEASUrement:IMMed:SOURCE2?` | :MEASUREMENT:IMMED:SOURCE2 CH1 | Conditions: This command applies to the TPS2000B/TPS2000 Series with TPS2PWR1 Power Analy… |
| `RS232?` | `RS232?` | :RS232:BAUD 9600;HARDFLAGGING 1;SOFTFLAGGING 0;PARITY NONE;TRANSMIT:T… | Group: RS-232 Commands (TDS2000, TDS1000, TDS200, TPS2000B, and TPS2000 Only) |
| `RS232:BAUd` | `RS232:BAUd?` | :RS232:BAUD 9600 | Conditions: This command applies to the TDS2000, TDS1000, TDS200, TPS2000B, and TPS2000 S… |
| `RS232:HARDFlagging` | `RS232:HARDFlagging?` | :RS232:HARDFLAGGING 1 | Conditions: This command applies to the TDS2000, TDS1000, TDS200, TPS2000B, and TPS2000 S… |
| `RS232:PARity` | `RS232:PARity?` | :RS232:PARITY NONE | Conditions: This command applies to the TDS2000, TDS1000, TDS200, TPS2000B, and TPS1000B … |
| `RS232:SOFTFlagging` | `RS232:SOFTFlagging?` | :RS232:SOFTFLAGGING 0 | Conditions: This command applies to the TDS2000, TDS1000, TDS200, TPS2000B, and TPS2000 S… |
| `RS232:TRANsmit:TERMinator` | `RS232:TRANsmit:TERMinator?` | :RS232:TRANSMIT:TERMINATOR LF | Conditions: This command applies to the TDS2000, TDS1000, TDS200, TPS2000B, and TPS2000 S… |

## (c) In `SET?` but not in the manual (1)

Headers in the `SET?` reply (`HEADer ON`, `VERBose ON`) that do not match any manual header, allowing for short forms and constructed mnemonics.

| Header in `SET?` | Value |
|---|---|
| `MEASUREMENT:METHOD` | AUTO |

## Documented for this model but not accepted (17)

| Header | Query sent | Result | Events |
|---|---|---|---|
| `WFMPre:NR_Pt?` | `WFMPre:NR_Pt?` | no_response | 2244, 420 |
| `WFMPre:PT_Fmt` | `WFMPre:PT_Fmt?` | no_response | 2244, 420 |
| `WFMPre:PT_Off` | `WFMPre:PT_Off?` | no_response | 2244, 420 |
| `WFMPre:WFId?` | `WFMPre:WFId?` | no_response | 2244, 420 |
| `WFMPre:XINcr` | `WFMPre:XINcr?` | no_response | 2244, 420 |
| `WFMPre:XUNit` | `WFMPre:XUNit?` | no_response | 2244, 420 |
| `WFMPre:XZEro` | `WFMPre:XZEro?` | no_response | 2244, 420 |
| `WFMPre:YMUlt` | `WFMPre:YMUlt?` | no_response | 2244, 420 |
| `WFMPre:YOFf` | `WFMPre:YOFf?` | no_response | 2244, 420 |
| `WFMPre:YUNit` | `WFMPre:YUNit?` | no_response | 2244, 420 |
| `WFMPre:YZEro` | `WFMPre:YZEro?` | no_response | 2244, 420 |
| `WFMPre:XMUlt` | `WFMPre:XMUlt?` | no_response | 100, 420 |
| `WFMPre:XOFf` | `WFMPre:XOFf?` | no_response | 100, 420 |
| `WFMPre:ZMUlt` | `WFMPre:ZMUlt?` | no_response | 100, 420 |
| `WFMPre:ZOFf` | `WFMPre:ZOFf?` | no_response | 100, 420 |
| `WFMPre:ZUNit` | `WFMPre:ZUNit?` | no_response | 100, 420 |
| `WFMPre:ZZEro` | `WFMPre:ZZEro?` | no_response | 100, 420 |

Event codes seen in this run (manual, Tables 3-5 to 3-8):

- `100`: Command error (Table 2-36 says the compatibility-only WFMPre headers give 100 and 420)
- `113`: Undefined header (the instrument does not know the command)
- `420`: Query UNTERMINATED (a reply was read for but none was produced)
- `2244`: Waveform requested is not activated

**Why the WFMPre queries above failed.** During the run `DATa:SOUrce` was `CH2` and CH2 was not displayed (`SELect:CH2 0`). The manual says the `WFMPre:<field>?` queries describe the `DATa:SOUrce` waveform and give event 2244 when it is not displayed. The same fields read through `WFMPre:CH1:<field>?` were all accepted. Changing `DATa:SOUrce` was out of scope (no writes except `HEADer` and `VERBose`). The six Table 2-36 headers gave 100 and 420, as the manual says.

**Timeouts.** The timeout was set to 3 s; with NI-VISA the wait measured about 5 s.
