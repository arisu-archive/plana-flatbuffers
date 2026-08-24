#!/bin/bash

# For each the .schema files, compile them into .go files
for schema in .schema/flatdata/*.fbs; do
    ./.scripts/flatc -o go -g --go-namespace flatdata --go-module-name github.com/arisu-archive/plana-flatbuffers/go "$schema"
    ./.scripts/flatc -o python --python --gen-object-api "$schema"
done

# Compile Excel schemas into Go and Python object APIs.
for schema in .schema/excel/*.fbs; do
    ./.scripts/flatc -o go -g --go-namespace excel --go-module-name github.com/arisu-archive/plana-flatbuffers/go "$schema"
    ./.scripts/flatc -o python --python --gen-object-api "$schema"
done
