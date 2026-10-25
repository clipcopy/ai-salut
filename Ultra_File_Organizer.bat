@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
title Ultra File Organizer

:: ============================================================
::  ULTRA FILE ORGANIZER
::  - Put this file in any folder and double-click it
::    (or drag a folder onto it) to sort that folder's files
::    into category folders: Images, Videos, Documents, etc.
::  - Never overwrites: duplicate names become name_1, name_2...
::  - Has an UNDO for the last run.
::  - Only sorts files directly inside the folder (not subfolders).
:: ============================================================

set "SELF=%~nx0"
set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=%~dp0"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
set "LOG=%TARGET%\_organizer_log.txt"

if not exist "%TARGET%\" (
    echo Folder not found: %TARGET%
    pause
    exit /b 1
)

:: ---------- Safety: never run on a drive root or system folders ----------
if "%TARGET:~-1%"==":" goto blocked
echo "%TARGET%"| findstr /i /c:"\Windows" /c:"Program Files" /c:"System32" >nul && goto blocked

:: ---------- Category lists (extensions) ----------
set "CATS=Images Videos Audio Documents Spreadsheets Presentations Ebooks Archives Disk_Images Programs Code Fonts"
set "L_Images=,jpg,jpeg,png,gif,bmp,webp,svg,ico,tif,tiff,heic,raw,psd,ai,"
set "L_Videos=,mp4,mkv,avi,mov,wmv,flv,webm,m4v,mpg,mpeg,3gp,"
set "L_Audio=,mp3,wav,flac,aac,ogg,m4a,wma,opus,mid,midi,"
set "L_Documents=,pdf,doc,docx,txt,rtf,odt,md,tex,log,"
set "L_Spreadsheets=,xls,xlsx,xlsm,csv,ods,tsv,"
set "L_Presentations=,ppt,pptx,odp,key,"
set "L_Ebooks=,epub,mobi,azw3,djvu,"
set "L_Archives=,zip,rar,7z,tar,gz,bz2,xz,tgz,"
set "L_Disk_Images=,iso,img,vhd,vhdx,vmdk,"
set "L_Programs=,exe,msi,apk,appx,msix,"
set "L_Code=,py,js,ts,html,htm,css,java,c,cpp,h,cs,php,json,xml,sh,bat,ps1,sql,yml,yaml,ini,"
set "L_Fonts=,ttf,otf,woff,woff2,"

:menu
cls
echo ==============================================
echo            ULTRA FILE ORGANIZER
echo ==============================================
echo  Folder: %TARGET%
echo.
echo   [1] Organize files into category folders
echo   [2] Undo the last organize
echo   [3] Exit
echo.
choice /c 123 /n /m "Choose 1, 2 or 3: "
if errorlevel 3 exit /b 0
if errorlevel 2 goto undo
if errorlevel 1 goto organize
goto menu

:organize
echo.
choice /c YN /n /m "Sort all files in this folder now? (Y/N): "
if errorlevel 2 goto menu
echo.
set "moved=0"
set "failed=0"
type nul > "%LOG%"
for /f "delims=" %%F in ('dir /b /a-d-h-s "%TARGET%"') do call :process "%%F"
attrib +h "%LOG%" >nul 2>&1
echo.
echo ----------------------------------------------
echo  Done. Moved: %moved%   Failed/skipped: %failed%
echo  You can undo this from the menu (option 2).
echo ----------------------------------------------
pause
goto menu

:undo
if not exist "%LOG%" (
    echo.
    echo Nothing to undo - no log found.
    pause
    goto menu
)
set "undone=0"
for /f "usebackq tokens=1,2 delims=?" %%A in ("%LOG%") do (
    move "%%B" "%%A" >nul 2>&1 && set /a undone+=1
)
for %%C in (%CATS% Other) do rmdir "%TARGET%\%%C" 2>nul
attrib -h "%LOG%" >nul 2>&1
del "%LOG%" >nul 2>&1
echo.
echo  Restored %undone% file(s). Empty category folders removed.
pause
goto menu

:blocked
echo.
echo  Blocked: this looks like a drive root or a system folder.
echo  Move this file into a normal folder (e.g. Downloads) and run it there.
pause
exit /b 1

:: ---------- Process one file ----------
:process
set "FNAME=%~1"
if /i "%FNAME%"=="%SELF%" exit /b
if /i "%FNAME%"=="_organizer_log.txt" exit /b
set "EXT=%~x1"
if defined EXT set "EXT=%EXT:~1%"
call :getcat
set "CAT=%found%"
set "DEST=%TARGET%\%CAT%"
if not exist "%DEST%\" mkdir "%DEST%"
set "NEWNAME=%~nx1"
set "N=0"
:chk
if not exist "%DEST%\%NEWNAME%" goto doit
set /a N+=1
set "NEWNAME=%~n1_%N%%~x1"
goto chk
:doit
move "%TARGET%\%~1" "%DEST%\%NEWNAME%" >nul 2>&1
if errorlevel 1 (
    set /a failed+=1
    exit /b
)
set /a moved+=1
set "line=%TARGET%\%~1?%DEST%\%NEWNAME%"
set "disp=  [%CAT%]  %~1"
setlocal EnableDelayedExpansion
>>"%LOG%" echo(!line!
echo(!disp!
endlocal
exit /b

:: ---------- Find category for %EXT% ----------
:getcat
set "found=Other"
if not defined EXT exit /b
setlocal EnableDelayedExpansion
set "e=,%EXT%,"
set "hit=Other"
for %%C in (%CATS%) do if "!hit!"=="Other" if not "!L_%%C:%e%=!"=="!L_%%C!" set "hit=%%C"
endlocal & set "found=%hit%"
exit /b
