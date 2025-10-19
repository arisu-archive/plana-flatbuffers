#!/bin/bash

# For each the .schema files, compile them into .go files
for schema in .schema/flatdata/*.fbs; do
    flatc -o go -g --go-namespace flatdata --go-module-name github.com/arisu-archive/plana-flatbuffers/go $schema
done

for schema in .schema/excel/*.fbs; do
    flatc -o go -g --go-namespace excel --go-module-name github.com/arisu-archive/plana-flatbuffers/go $schema
done
