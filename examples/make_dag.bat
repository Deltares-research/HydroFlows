@echo off

echo Activating the python environment
call activate hydroflows

echo Creating an image of the Directed Acyclic Graph (DAG) for %1
snakemake -s %1 --configfile %2 --dag | dot -Tsvg > tmp/dag.svg

pause
