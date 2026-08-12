# Testing Guide

> **Historical reference — these are not current project test commands.**

## 1. Unit Tests

Run the full test suite:

```bash
cd PaddleOCR
python -m pytest tests/ -v
```

Run specific tests:

```bash
# Test OCR pipeline
python -m pytest tests/test_ocr.py -v

# Test structure detection
python -m pytest tests/test_structure.py -v

# Test specific module
python -m pytest tests/ppocr_test.py -v
```

## 2. Benchmarking

### End-to-End Benchmark

```bash
python -m paddleocr.benchmark --engine paddle
python -m paddleocr.benchmark --engine transformers
```

### Fine-Grained Benchmarking

For detailed performance analysis:

```bash
python -m paddleocr.benchmark --benchmark-detail --device gpu
python -m paddleocr.benchmark --benchmark-detail --device cpu
```

### Hardware-Specific Benchmarks

Refer to the [official documentation](https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/pipeline_usage/instructions/benchmark.en.md) for benchmark results on mainstream hardware configurations.

## 3. Manual Testing

### Basic OCR Test

```bash
# Test OCR with demo image
paddleocr ocr -i ./general_ocr_002.png --engine paddle

# Test OCR with Transformers backend
paddleocr ocr -i ./general_ocr_002.png --engine transformers
```

### Text Detection Test

```bash
paddleocr text_detection -i ./general_ocr_001.png --engine paddle
paddleocr text_detection -i ./general_ocr_001.png --engine transformers
```

### Text Recognition Test

```bash
paddleocr text_recognition -i ./general_ocr_rec_001.png --engine paddle
paddleocr text_recognition -i ./general_ocr_rec_001.png --engine transformers
```

### Structure Detection Test

```bash
paddleocr pp_structurev3 -i ./pp_structure_v3_demo.png --engine paddle
paddleocr pp_structurev3 -i ./pp_structure_v3_demo.png --engine transformers
```

### Python API Test

```python
from paddleocr import PaddleOCR

# Test basic functionality
ocr = PaddleOCR(engine="paddle")
result = ocr.predict("./general_ocr_002.png")

for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")
```

## 4. Integration Testing

### Test with Different Image Formats

```bash
# Test with various formats
for img in *.png *.jpg *.jpeg *.bmp *.tiff; do
    paddleocr ocr -i "$img" --engine paddle
done
```

### Test with PDF Input

```bash
# Convert PDF to images first
pdftoppm input.pdf output -png
paddleocr ocr -i output-1.png --engine paddle
```

## 5. Performance Testing

### Latency Measurement

```python
import time
from paddleocr import PaddleOCR

ocr = PaddleOCR(engine="paddle")

# Warmup
ocr.predict("general_ocr_002.png")

# Measure latency
start = time.time()
for _ in range(10):
    ocr.predict("general_ocr_002.png")
end = time.time()

print(f"Average latency: {(end - start) / 10:.3f}s")
```

### Throughput Testing

```bash
# Using the benchmark tool
python -m paddleocr.benchmark \
    --model pp_ocr_v6 \
    --device gpu \
    --iterations 100 \
    --batch-size 1
```

## 6. Validation Scripts

### Verify Installation

```python
import paddle
import paddleocr

print(f"PaddlePaddle version: {paddle.__version__}")
print(f"PaddleOCR version: {paddleocr.__version__}")
print(f"GPU available: {paddle.is_compiled_with_cuda()}")

# Quick test
ocr = paddleocr.PaddleOCR(engine="paddle")
result = ocr.predict("general_ocr_002.png")
print("Installation verified!")
```

### Model Integrity Check

```python
from paddleocr import PaddleOCR
import os

# Check if models are downloaded correctly
ocr = PaddleOCR(engine="paddle")

# Verify model files exist
model_dirs = [
    "~/.paddleocr/models/pp_ocr_v6",
    "~/.paddleocr/models/pp_structure_v3"
]

for dir_path in model_dirs:
    expanded = os.path.expanduser(dir_path)
    if os.path.exists(expanded):
        print(f"✓ {dir_path} exists")
    else:
        print(f"✗ {dir_path} missing")
```
