#!/bin/bash

# Process the flatbuffers files
go run github.com/arisu-archive/bluearchive-fbs-generator@latest -i ./.schema/flatdata -o ./go/flatdata -p flatdata
go run github.com/arisu-archive/bluearchive-fbs-generator@latest -i ./.schema/excel -o ./go/excel -p excel -without-decryption
# Run fbsprocessor from its own directory to use its go.mod
(cd cmd/tools/fbsprocessor && go run . -dir ../../../go/flatdata -lang go -p flatdata)
(cd cmd/tools/fbsprocessor && go run . -dir ../../../go/excel -lang go -p excel)

go mod tidy
