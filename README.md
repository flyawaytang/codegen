# PDF File Embedder

A Python tool for embedding files into PDF documents using pikepdf, with automatic object number management.

## Features

- Embed files into PDF documents
- Automatically find free object numbers in the PDF
- Analyze PDF object structure
- Extract embedded files from PDFs
- Support for various file types with MIME type detection

## Requirements

- Python 3.6+
- pikepdf library

## Installation

```bash
pip install pikepdf
```

## Usage

### Embedding a File

```bash
python pdf_file_embedder_final.py input.pdf file_to_embed.txt output.pdf
```

### Analyzing a PDF

```bash
python pdf_file_embedder_final.py input.pdf --analyze-only
```

### Extracting Embedded Files

```bash
python pdf_file_embedder_final.py input.pdf --extract --output-dir ./extracted
```

### Specifying MIME Type

```bash
python pdf_file_embedder_final.py input.pdf file_to_embed.bin output.pdf --mime-type application/octet-stream
```

## How It Works

1. The script opens the input PDF using pikepdf
2. It scans all objects in the PDF to identify used object numbers
3. It finds available (free) object numbers
4. When embedding a file, it creates a new stream object and file specification
5. The embedded file is added to the PDF's Names dictionary under EmbeddedFiles
6. The modified PDF is saved to the output file

## Object Number Management

The script automatically:
- Identifies all used object numbers in the PDF
- Finds available object numbers
- Reports the object number assigned to the embedded file

## Example Output

```
PDF Version: 1.7
Number of Pages: 5
Total objects: 157
Maximum object number: 157
Available free object numbers: [158, 159, 160, 161, 162, 163, 164, 165, 166, 167]...

Embedding file: secret.txt
Embedded file object number: 158
File specification object number: 159
Modified PDF saved to: output.pdf

Verifying embedded file...
Verification successful: Found embedded file 'secret.txt'
```

## License

MIT

