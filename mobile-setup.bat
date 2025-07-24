@echo off
setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Create mobile.bat in the same directory
echo @echo off > "%SCRIPT_DIR%mobile.bat"
echo setlocal EnableDelayedExpansion >> "%SCRIPT_DIR%mobile.bat"
echo. >> "%SCRIPT_DIR%mobile.bat"
echo REM Default values >> "%SCRIPT_DIR%mobile.bat"
echo set MODEL=gemini >> "%SCRIPT_DIR%mobile.bat"
echo set INTERACTIVE= >> "%SCRIPT_DIR%mobile.bat"
echo set PROMPT= >> "%SCRIPT_DIR%mobile.bat"
echo. >> "%SCRIPT_DIR%mobile.bat"
echo REM Parse arguments >> "%SCRIPT_DIR%mobile.bat"
echo :parse_args >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="" goto :execute >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="--claude" ( >> "%SCRIPT_DIR%mobile.bat"
echo     set MODEL=claude >> "%SCRIPT_DIR%mobile.bat"
echo     shift >> "%SCRIPT_DIR%mobile.bat"
echo     goto :parse_args >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="--gemini" ( >> "%SCRIPT_DIR%mobile.bat"
echo     set MODEL=gemini >> "%SCRIPT_DIR%mobile.bat"
echo     shift >> "%SCRIPT_DIR%mobile.bat"
echo     goto :parse_args >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="-i" ( >> "%SCRIPT_DIR%mobile.bat"
echo     set INTERACTIVE=true >> "%SCRIPT_DIR%mobile.bat"
echo     shift >> "%SCRIPT_DIR%mobile.bat"
echo     goto :parse_args >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="--interactive" ( >> "%SCRIPT_DIR%mobile.bat"
echo     set INTERACTIVE=true >> "%SCRIPT_DIR%mobile.bat"
echo     shift >> "%SCRIPT_DIR%mobile.bat"
echo     goto :parse_args >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="-h" ( >> "%SCRIPT_DIR%mobile.bat"
echo     goto :help >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo if "%%~1"=="--help" ( >> "%SCRIPT_DIR%mobile.bat"
echo     goto :help >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo. >> "%SCRIPT_DIR%mobile.bat"
echo REM Collect remaining arguments as prompt >> "%SCRIPT_DIR%mobile.bat"
echo set PROMPT=!PROMPT! %%1 >> "%SCRIPT_DIR%mobile.bat"
echo shift >> "%SCRIPT_DIR%mobile.bat"
echo goto :parse_args >> "%SCRIPT_DIR%mobile.bat"
echo. >> "%SCRIPT_DIR%mobile.bat"
echo :execute >> "%SCRIPT_DIR%mobile.bat"
echo cd /d "%SCRIPT_DIR%" >> "%SCRIPT_DIR%mobile.bat"
echo if defined INTERACTIVE ( >> "%SCRIPT_DIR%mobile.bat"
echo     echo Starting interactive mobile automation with %%MODEL%%... >> "%SCRIPT_DIR%mobile.bat"
echo     python run_agent.py --model %%MODEL%% --interactive >> "%SCRIPT_DIR%mobile.bat"
echo ^) else if defined PROMPT ( >> "%SCRIPT_DIR%mobile.bat"
echo     python run_agent.py --model %%MODEL%% --prompt "!PROMPT!" >> "%SCRIPT_DIR%mobile.bat"
echo ^) else ( >> "%SCRIPT_DIR%mobile.bat"
echo     echo Starting interactive mobile automation with %%MODEL%%... >> "%SCRIPT_DIR%mobile.bat"
echo     python run_agent.py --model %%MODEL%% --interactive >> "%SCRIPT_DIR%mobile.bat"
echo ^) >> "%SCRIPT_DIR%mobile.bat"
echo goto :eof >> "%SCRIPT_DIR%mobile.bat"
echo. >> "%SCRIPT_DIR%mobile.bat"
echo :help >> "%SCRIPT_DIR%mobile.bat"
echo echo Mobile Automation Agent >> "%SCRIPT_DIR%mobile.bat"
echo echo. >> "%SCRIPT_DIR%mobile.bat"
echo echo Usage: >> "%SCRIPT_DIR%mobile.bat"
echo echo   mobile "Launch Settings"                     - Single command ^(default: gemini^) >> "%SCRIPT_DIR%mobile.bat"
echo echo   mobile --claude "Open Instagram"             - Single command with Claude >> "%SCRIPT_DIR%mobile.bat"
echo echo   mobile --gemini "Calculate 15 + 25"          - Single command with Gemini >> "%SCRIPT_DIR%mobile.bat"
echo echo   mobile -i                                    - Interactive mode >> "%SCRIPT_DIR%mobile.bat"
echo echo   mobile --claude -i                           - Interactive mode with Claude >> "%SCRIPT_DIR%mobile.bat"
echo echo. >> "%SCRIPT_DIR%mobile.bat"
echo echo Flags: >> "%SCRIPT_DIR%mobile.bat"
echo echo   --claude     Use Claude model >> "%SCRIPT_DIR%mobile.bat"
echo echo   --gemini     Use Gemini model ^(default^) >> "%SCRIPT_DIR%mobile.bat"
echo echo   -i           Interactive mode >> "%SCRIPT_DIR%mobile.bat"
echo echo   -h           Show this help >> "%SCRIPT_DIR%mobile.bat"
echo goto :eof >> "%SCRIPT_DIR%mobile.bat"

REM Add current directory to PATH for this session
set "PATH=%SCRIPT_DIR%;%PATH%"

echo Mobile automation command created!
echo.
echo Usage: mobile "Launch Settings on iPhone"
echo        mobile -i
echo        mobile --claude "Open Instagram"
echo.
echo The 'mobile' command is now available for this session.
echo.
echo To make this permanent, add this directory to your system PATH:
echo %SCRIPT_DIR%
echo.
echo Or run this setup script each time you open a new command prompt.

endlocal
