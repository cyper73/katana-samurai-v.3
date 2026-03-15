# Katana Agent - Scanned PDF Processor

## Description

The Katana Agent is an advanced system for processing scanned PDF documents. The system is capable of:

- ✅ Examining scanned PDFs
- ✅ Extracting DPI metadata and resolutions
- ✅ Detecting scanned images per page
- ✅ Cropping and resizing images
- ✅ Converting to single JPG format
- ✅ Preserving original image appearance
- ✅ Automatic content detection

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR (optional)

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to system PATH

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

## Usage

### Command Line Interface (CLI)

Katana offers a complete CLI for document processing. Run `python katana.py` without arguments to view help.

```bash
python katana.py <input_file_or_dir> [options]
```

**Options:**
- `--output-dir DIR`: Output directory (default: output_images)
- `--dpi DPI`: Target DPI (default: 300)
- `--no-crop`: Disable automatic cropping
- `--format FMT`: Target format (A4, A3, LETTER, LEGAL)
- `--test-ratio`: Run ratio detection test

**Examples:**

```bash
# Process a single A4 PDF
python katana.py document.pdf --format A4

# Process all PDFs in a directory
python katana.py .
```

### Quality Control and Testing

To verify system integrity and core functionalities:

```bash
# Runs compilation, metadata test, and autocrop test
check_quality.bat
```

### Performance Optimizations

The system includes automatic optimizations for large images:
- **Fast Color Analysis**: Smart timeout (10s) to avoid blocking
- **Adaptive Sampling**: Drastically reduces time on images >4000px
- **Hybrid Resizing**: Smart handling of out-of-format images

### Advanced Options

```bash
# Specify output directory
python katana.py document.pdf --output-dir ./processed_images

# Set custom DPI
python katana.py document.pdf --dpi 600

# Disable automatic cropping
python katana.py document.pdf --no-crop

# Verbose output
python katana.py document.pdf --verbose
```

## Main Features

### 1. Metadata Extraction
- DPI and resolution analysis
- Page information
- Embedded image details

### 2. Image Processing
- Direct image extraction from PDF
- Page rendering as high-resolution images
- Preservation of original appearance without color or contrast modification

### 3. Smart Cropping
- Automatic document edge detection
- Removal of margins and white spaces
- Preservation of main content

### 4. Quality Optimization
- Smart resizing
- Original color preservation
- Natural appearance maintenance
- Optimized JPG conversion

## Output Structure

The system creates an `output_images` directory (or specified one) containing:

```
output_images/
├── document_page_1_img_1.jpg          # Original extracted image
├── document_page_1_img_1_cropped.jpg  # Cropped image
├── document_page_2_rendered.jpg       # Rendered page
└── katana_report_YYYYMMDD_HHMMSS.txt  # Detailed report
```

## Logging

The system automatically generates:
- `katana.log` - Detailed operation log
- Final report with processing statistics

## Libraries Used

- **PyMuPDF (fitz)** - PDF processing
- **OpenCV** - Image processing and edge detection
- **Pillow (PIL)** - Image manipulation
- **NumPy** - Numerical operations
- **pytesseract** - OCR (optional)

## Usage Examples

### Batch Processing

```python
from katana import KatanaProcessor

# Initialize processor
processor = KatanaProcessor("./output")

# Process all PDFs in current directory
results = processor.process_directory(".", target_dpi=300, crop_content=True)

# Generate report
report = processor.generate_report()
print(report)
```

### Single Processing

```python
from katana import KatanaProcessor

processor = KatanaProcessor()
result = processor.process_pdf_file("document.pdf", target_dpi=600)

if result['success']:
    print(f"Processed {len(result['output_images'])} images")
else:
    print(f"Errors: {result['errors']}")
```

## Troubleshooting

### Error: "Cannot import fitz"
```bash
pip install PyMuPDF
```

### Error: "Tesseract not found"
- Verify Tesseract OCR installation
- Add Tesseract to system PATH

### Low Quality Images
- Increase target DPI: `--dpi 600`
- Check original PDF quality

## Contributions

To contribute to the project:
1. Fork the repository
2. Create a branch for changes
3. Test changes
