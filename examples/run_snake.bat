@echo off

echo Activating the python environment
call activate hydroflows

echo Unlocking the directory
snakemake --unlock -s %1 --configfile %2

echo Executing Snakefile %1 with config %2
snakemake all -s %1 -c 4 --configfile %2  --rerun-incomplete

pause
