package languages

import (
	"context"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
	"text/template"
)

var _ LanguageProcessor = (*GoProcessor)(nil)

// GoProcessor handles post-processing of Go FlatBuffer files.
type GoProcessor struct {
	flatbuffers map[string]string
	packageName string
}

// NewGoProcessor creates a new Go processor.
func NewGoProcessor() *GoProcessor {
	return &GoProcessor{
		flatbuffers: map[string]string{},
	}
}

// SetPackageName sets the package name for the language processor.
func (p *GoProcessor) SetPackageName(packageName string) {
	p.packageName = packageName
}

// ProcessFile adds encryption to a Go FlatBuffer file.
func (p *GoProcessor) ProcessFile(filePath string) error {
	// Parse the Go file using go parser, go/parser is used to parse the file and return the AST.
	fset := token.NewFileSet()
	tree, err := parser.ParseFile(fset, filePath, nil, parser.ParseComments)
	if err != nil {
		return fmt.Errorf("failed to parse file %s: %w", filePath, err)
	}
	// Check the imports for flatbuffers
	dtoName := p.dumpFlatDataModels(tree)
	if dtoName == "" {
		return fmt.Errorf("failed to dump flat data models: %w", err)
	}
	p.flatbuffers[strings.ToLower(strings.ReplaceAll(dtoName, "Dto", ""))] = dtoName

	return nil
}

func (*GoProcessor) dumpFlatDataModels(tree *ast.File) string {
	for _, decl := range tree.Decls {
		genDecl, ok := decl.(*ast.GenDecl)
		if !ok || genDecl.Tok != token.TYPE {
			continue
		}

		for _, spec := range genDecl.Specs {
			typeSpec, ok := spec.(*ast.TypeSpec)
			if !ok {
				continue
			}

			structType, ok := typeSpec.Type.(*ast.StructType)
			if !ok {
				continue
			}
			for _, field := range structType.Fields.List {
				if field.Type == nil {
					continue
				}
				selector, ok := field.Type.(*ast.SelectorExpr)
				if !ok {
					continue
				}
				if selector.X.(*ast.Ident).Name == "fbsutils" && selector.Sel.Name == "FlatBuffer" {
					return typeSpec.Name.Name
				}
			}
		}
	}
	return ""
}

// Extension returns the file extension for the language.
func (*GoProcessor) Extension() string {
	return ".go"
}

const (
	FlatDataHelperFileName = "flatdatas_helper.go"
)

func (*GoProcessor) PreProcess(context.Context, string) error {
	return nil
}

func (p *GoProcessor) PostProcess(_ context.Context, outputDir string) error {
	// Create a new file: flatdatas_helper.go
	// Create a global variable: fbs and set it to the flatbuffers package
	// Create a function: GetFlatDataByName(name string)
	f, osErr := os.Create(filepath.Join(outputDir, FlatDataHelperFileName))
	if osErr != nil {
		return fmt.Errorf("failed to create file: %w", osErr)
	}
	defer f.Close()

	// Write the file
	tmpl, err := template.New("flatbufferCode").Parse(flatbufferCode)
	if err != nil {
		return fmt.Errorf("failed to parse template: %w", err)
	}
	// Execute the template. Output the result to the file
	if executeErr := tmpl.Execute(f, map[string]interface{}{
		"Package":     p.packageName,
		"Flatbuffers": p.flatbuffers,
	}); executeErr != nil {
		return fmt.Errorf("failed to execute template: %w", executeErr)
	}
	return nil
}

const flatbufferCode = `package {{ .Package }}

import (
	"reflect"

	fbsutils "github.com/arisu-archive/bluearchive-fbs-utils"
)

var fbs = map[string]reflect.Type{
{{- range $key, $value := .Flatbuffers }}
	"{{ $key }}": reflect.TypeOf((*{{ $value }})(nil)).Elem(),
{{- end }}
}

func GetFlatDataByName(name string) fbsutils.FlatData {
	if data, ok := fbs[name]; ok {
		return reflect.New(data).Interface().(fbsutils.FlatData)
	}
	return nil
}
`
