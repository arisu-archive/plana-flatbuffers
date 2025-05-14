#!/bin/bash

# Process the flatbuffers files
go run github.com/arisu-archive/bluearchive-fbs-generator@latest -i ./.schema/flatdata -o ./go/flatdata -p flatdata
go run github.com/arisu-archive/bluearchive-fbs-generator@latest -i ./.schema/excel -o ./go/excel -p excel -without-decryption
go run ./cmd/tools/fbsprocessor/main.go -dir ./go/flatdata -lang go -p flatdata
go run ./cmd/tools/fbsprocessor/main.go -dir ./go/excel -lang go -p excel
go mod tidy
