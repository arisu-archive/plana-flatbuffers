#!/bin/bash

# For each the .schema files, compile them into .go files
for schema in .schema/flatdata/*.fbs; do
    flatc -o go -g --go-namespace flatdata $schema
    flatc -o python -p $schema
done

for schema in .schema/excel/*.fbs; do
    flatc -o go -g --go-namespace excel $schema
    flatc -o python -p $schema
done
