package languages

import "context"

// LanguageProcessor defines the interface for language-specific processors.
type LanguageProcessor interface {
	// ProcessFile adds encryption to a FlatBuffer-generated file
	ProcessFile(filePath string) error

	// Extension returns the file extension for the language
	Extension() string

	// PreProcess is called before the processing of the files starts
	PreProcess(ctx context.Context, outputDir string) error

	// PostProcess is called after the processing of the files starts
	PostProcess(ctx context.Context, outputDir string) error

	// SetPackageName sets the package name for the language processor
	SetPackageName(packageName string)
}
