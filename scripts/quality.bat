@echo off
setlocal

call :run isort . ^
&& call :run black . ^
&& call :run flake8 . ^
&& call :run pylint --spelling-dict=en_GB . ^
&& call :run djlint --check . ^
&& call :run mypy .
if errorlevel 1 exit /b %errorlevel%

echo All quality checks passed.
exit /b 0

:run
echo ==^> %*
%*
if errorlevel 1 exit /b %errorlevel%
exit /b 0
