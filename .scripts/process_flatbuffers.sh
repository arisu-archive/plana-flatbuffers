#!/bin/bash
set -euo pipefail

# Process the flatbuffers files
go run github.com/arisu-archive/bluearchive-fbs-generator@latest -i ./.schema/flatdata -o ./go/flatdata -p flatdata
go run github.com/arisu-archive/bluearchive-fbs-generator@latest -i ./.schema/excel -o ./go/excel -p excel -without-decryption
# Run fbsprocessor from its own directory to use its go.mod
(cd cmd/tools/fbsprocessor && go run . -dir ../../../go/flatdata -lang go -p flatdata)
(cd cmd/tools/fbsprocessor && go run . -dir ../../../go/excel -lang go -p excel)

# Install conversion behavior for FlatData object APIs and generate lazy model registries.
python3 ./.scripts/process_python_object_api.py --directory ./python/FlatData --package FlatData
python3 ./.scripts/process_python_object_api.py --directory ./python/MX/Data/Excel --package MX.Data.Excel --without-decryption

go mod tidy
