package fbstools

import "log/slog"

type ProcessorOptions struct {
	Directory string
	Package   string
	Language  Language
	DryRun    bool
}

type ProcessorOption func(*Processor)

func WithLogger(logger *slog.Logger) ProcessorOption {
	return func(p *Processor) {
		p.logger = logger
	}
}
