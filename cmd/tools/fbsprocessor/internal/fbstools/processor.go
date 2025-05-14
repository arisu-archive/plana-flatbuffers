package fbstools

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"sync"

	"github.com/bmatcuk/doublestar/v4"

	"github.com/arisu-archive/plana-flatbuffers/cmd/tools/fbsprocessor/internal/fbstools/languages"
)

// processors is a map of language to processor.
var processors sync.Map //nolint:gochecknoglobals // processor is a singleton.

//nolint:gochecknoinits // processor is a singleton.
func init() {
	processors.Store(Go, languages.NewGoProcessor())
}

// Processor is a processor for a specific language.
type Processor struct {
	logger  *slog.Logger
	opts    ProcessorOptions
	handler languages.LanguageProcessor
}

// NewProcessor creates a new processor for a specific language.
func NewProcessor(opts ProcessorOptions, optsFuncs ...func(*Processor)) *Processor {
	handler, ok := processors.Load(opts.Language)
	if !ok {
		panic(fmt.Sprintf("language %s not supported", opts.Language))
	}
	handler.(languages.LanguageProcessor).SetPackageName(opts.Package)
	p := &Processor{
		opts:    opts,
		handler: handler.(languages.LanguageProcessor), //nolint:errcheck // processor must be language processor.
	}
	for _, opt := range optsFuncs {
		opt(p)
	}
	return p
}

func (p *Processor) Process(ctx context.Context) error {
	// WalkThrough the input folder and process each file
	files, walkErr := p.walkDir()
	if walkErr != nil {
		return fmt.Errorf("failed to walk directory %s: %w", p.opts.Directory, walkErr)
	}

	// Notify the handler we are starting
	if err := p.handler.PreProcess(ctx, p.opts.Directory); err != nil {
		return fmt.Errorf("failed to pre process files: %w", err)
	}

	for _, file := range files {
		fullPath := filepath.Join(p.opts.Directory, file)
		if err := p.handler.ProcessFile(fullPath); err != nil {
			p.logger.DebugContext(ctx, "failed to process file", "file", file, "error", err)
		}
	}

	// Notify the handler we are done
	if err := p.handler.PostProcess(ctx, p.opts.Directory); err != nil {
		return fmt.Errorf("failed to post process files: %w", err)
	}
	return nil
}

func (p *Processor) walkDir() ([]string, error) {
	fs := os.DirFS(p.opts.Directory)
	files, err := doublestar.Glob(fs, "**/*"+p.handler.Extension())
	if err != nil {
		return nil, fmt.Errorf("failed to glob directory %s: %w", p.opts.Directory, err)
	}
	return files, nil
}
