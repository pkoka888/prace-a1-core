# CLI Reference

> **Historical reference — commands are not active project instructions.**

## 1. Global Options

```bash
paddleocr [COMMAND] [OPTIONS] [ARGS...]

# Help
paddleocr --help
paddleocr <command> --help
```

## 2. Commands

### 2.1 OCR Pipeline

```bash
paddleocr ocr -i <input_image> [OPTIONS]

Options:
  -i, --input PATH            Input image or directory path
  --engine TEXT              Inference engine: paddle or transformers [default: paddle]
  --use_doc_orientation_classify BOOLEAN   Enable document orientation classification [default: True]
  --use_doc_unwarping BOOLEAN              Enable document unwarping [default: True]
  --use_textline_orientation BOOLEAN       Enable text line orientation detection [default: True]
  --output PATH              Output directory for results [default: output]
  --save-img                 Save visualization images
  --save-json                Save JSON results
```

### 2.2 Text Detection

```bash
paddleocr text_detection -i <input_image> [OPTIONS]

Options:
  -i, --input PATH            Input image path
  --engine TEXT              Inference engine: paddle or transformers [default: paddle]
  --output PATH              Output directory [default: output]
```

### 2.3 Text Recognition

```bash
paddleocr text_recognition -i <input_image> [OPTIONS]

Options:
  -i, --input PATH            Input image path
  --engine TEXT              Inference engine: paddle or transformers [default: paddle]
  --output PATH              Output directory [default: output]
```

### 2.4 Structure Detection (PP-StructureV3)

```bash
paddleocr pp_structurev3 -i <input_image> [OPTIONS]

Options:
  -i, --input PATH            Input image path
  --engine TEXT              Inference engine: paddle or transformers [default: paddle]
  --use_doc_orientation_classify BOOLEAN   Enable document orientation classification [default: True]
  --use_doc_unwarping BOOLEAN              Enable document unwarping [default: True]
  --use_formula_recognition BOOLEAN        Enable formula recognition [default: True]
  --use_chart_parsing BOOLEAN              Enable chart parsing [default: True]
  --wireless_table_structure_recognition_model_name TEXT  Table structure model [default: SLANeXt_wireless]
  --output PATH              Output directory [default: output]
  --save-img                 Save visualization images
  --save-json                Save JSON results
  --save-markdown            Save Markdown results
```

### 2.5 Other Commands

```bash
# Model management
paddleocr download --model pp_ocr_v6
paddleocr download --model pp_structure_v3

# Version info
paddleocr version
paddleocr --version
```

## 3. Examples

### Basic OCR
```bash
# CPU with PaddlePaddle engine
paddleocr ocr -i ./example.png --engine paddle

# GPU with PaddlePaddle engine
paddleocr ocr -i ./example.png --engine paddle --device gpu

# Transformers backend
paddleocr ocr -i ./example.png --engine transformers
```

### With Output Options
```bash
# Save images and JSON
paddleocr ocr -i ./example.png --engine paddle \
    --save-img --save-json --output ./results/

# Disable preprocessing for faster speed
paddleocr ocr -i ./example.png --engine paddle \
    --use_doc_orientation_classify False \
    --use_doc_unwarping False \
    --use_textline_orientation False
```

### Structure Detection
```bash
# Full structure detection
paddleocr pp_structurev3 -i ./document.png --engine paddle \
    --save-img --save-json --save-markdown --output ./structure_results/

# Transformers backend with formula recognition disabled
paddleocr pp_structurev3 -i ./document.png --engine transformers \
    --use_formula_recognition False \
    --wireless_table_structure_recognition_model_name SLANeXt_wireless
```

### Batch Processing
```bash
# Process multiple images
for img in *.png; do
    paddleocr ocr -i "$img" --engine paddle --output "results_${img%.*}"
done

# Process directory (if supported)
paddleocr ocr -i ./images/ --engine paddle --output ./batch_results/
```

### Environment Variables
```bash
# Set CUDA device
export CUDA_VISIBLE_DEVICES=0
paddleocr ocr -i ./example.png --engine paddle

# Use CPU only
export CUDA_VISIBLE_DEVICES=""
paddleocr ocr -i ./example.png --engine paddle

# Debug mode
export PADDLE_OCR_DEBUG=1
paddleocr ocr -i ./example.png --engine paddle --log-level DEBUG
```

## 4. Common Flags Summary

| Flag | Description | Default |
|------|-------------|---------|
| `-i, --input` | Input path | Required |
| `--engine` | Inference backend | `paddle` |
| `--output` | Output directory | `output` |
| `--save-img` | Save visualization | False |
| `--save-json` | Save JSON output | False |
| `--save-markdown` | Save Markdown output | False |
| `--use_doc_orientation_classify` | Enable orientation classification | True |
| `--use_doc_unwarping` | Enable unwarping | True |
| `--use_textline_orientation` | Enable text line orientation | True |
| `--use_formula_recognition` | Enable formula recognition | True |
| `--log-level` | Logging level | INFO |

## 5. Output Formats

### JSON Output
```json
{
  "res": {
    "input_path": "./example.png",
    "dt_polys": [...],
    "rec_texts": ["text1", "text2"],
    "rec_scores": [0.99, 0.98]
  }
}
```

### Markdown Output
```markdown
# Document Title

## Section 1

Text content here...

| Table Header 1 | Table Header 2 |
|----------------|----------------|
| Cell 1         | Cell 2         |
```

## 6. Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Model loading error |
| 4 | Input file error |
| 5 | Inference error |

## 7. Performance Tips

1. **Use `--engine paddle`** for faster inference on NVIDIA GPUs
2. **Disable preprocessing** (`--use_doc_orientation_classify False --use_doc_unwarping False`) for speed
3. **Use specific models** for your use case
4. **Batch process** multiple images
5. **Use smaller models** for edge deployment
