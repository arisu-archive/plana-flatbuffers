package main

import (
	"context"
	"flag"
	"log/slog"
	"os"
	"strings"

	"github.com/arisu-archive/plana-flatbuffers/cmd/tools/fbsprocessor/internal/fbstools"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))

	// Parse command line flags
	dirFlag := flag.String("dir", "", "Directory containing generated FlatBuffer files")
	langFlag := flag.String("lang", "", "Language to process (go)")
	packageFlag := flag.String("p", "", "Package name")
	flag.Parse()

	if *dirFlag == "" {
		logger.Error("Error: Missing required --dir flag")
		flag.Usage()
		os.Exit(1)
	}

	if *packageFlag == "" {
		logger.Error("Error: Missing required --p flag")
		flag.Usage()
		os.Exit(1)
	}

	// Determine which languages to process
	var lang fbstools.Language
	switch strings.ToLower(*langFlag) {
	case "go":
		lang = fbstools.Go
	default:
		logger.Error("Error: Unsupported language", "language", *langFlag)
		os.Exit(1)
	}

	// Create processor options
	opts := fbstools.ProcessorOptions{
		Directory: *dirFlag,
		Language:  lang,
		Package:   *packageFlag,
	}

	// Create processor
	processor := fbstools.NewProcessor(opts, fbstools.WithLogger(logger))

	// Process files
	err := processor.Process(context.Background())
	if err != nil {
		logger.Error("Error processing files", "error", err)
		os.Exit(1)
	}
}
