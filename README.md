# Plana Flatbuffers

This repository contains the Flatbuffers schema and generated code for the Plana project, which processes Plana game data.

## Overview

Plana Flatbuffers is a tool that generates and maintains Flatbuffers schema definitions for Plana game data. It automatically tracks game version updates and generates corresponding schema files.

## Prerequisites

- [Go](https://go.dev/dl/) ≥ 1.22
- [flatc](https://github.com/google/flatbuffers/tree/master/flatc) ≥ 1.69

## Generated Code

This repository provides:
- FlatBuffers schema files (`.fbs`)
- Pre-generated Go code with `flatdata` namespace

You can directly use these generated files in your projects without needing to compile the schemas yourself.

## Using the Generated Code

### For Go Projects

1. Import the generated code in your Go project:
```go
import "github.com/arisu-archive/plana-flatbuffers/go/flatdata"
```

## Development Prerequisites

If you want to contribute or regenerate the code:

- [flatc](https://github.com/google/flatbuffers/tree/master/flatc) ≥ 1.69

## Project Structure

```
.
├── .schema/          # FlatBuffers schema files
├── .scripts/         # Utility scripts for code generation
├── go/              # Generated Go code
└── version.txt      # Current APK version tracker
```

## Automatic Updates

This repository features an automated GitHub Actions workflow that:
1. Monitors the Game APK updates
2. Downloads and processes the latest game data
3. Generates updated schema files
4. Updates the generated code
5. Creates a pull request with the changes

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This project is part of the Plana ecosystem
- Uses Google's FlatBuffers for efficient serialization
