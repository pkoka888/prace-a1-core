# Diagnostic Guide

> **Historical reference — do not apply these procedures to the active project.**

## 1. Common Issues and Solutions

### Installation Issues

**Problem**: Installation fails or packages are not available

**Solution**:
```bash
# Check Python version
python --version

# Check pip version
pip --version

# Try with verbose output
python -m pip install --verbose "paddleocr[all]"

# Use specific mirrors
python -m pip install paddlepaddle==3.2.0 --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

### GPU Issues

**Problem**: CUDA/GPU not detected or not working

**Diagnostic Commands**:
```bash
# Check CUDA installation
nvidia-smi

# Check CUDA toolkit version
nvcc --version

# Check PaddlePaddle GPU support
python -c "import paddle; print('CUDA compiled:', paddle.is_compiled_with_cuda())"

# Check GPU devices in Python
python -c "import paddle; print('GPU devices:', paddle.device.get_device())"
```

**Solutions**:
1. Install compatible CUDA version (check PaddlePaddle requirements)
2. Set CUDA path: `export PATH=/usr/local/cuda/bin:$PATH`
3. Set LD_LIBRARY_PATH: `export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH`
4. Update kernel driver

### Memory Issues

**Problem**: Insufficient GPU memory

**Diagnostic Commands**:
```bash
# Check GPU memory
nvidia-smi

# Check system memory
free -h
```

**Solutions**:
1. Reduce batch size: `batch_size=1`
2. Use CPU mode for testing
3. Use mixed precision: `PADDLE_PRECISION=fp16`
4. Clear unused memory: `import paddle; paddle.device.cuda.empty_cache()`

### Permission Issues

**Problem**: Permission denied when accessing files

**Diagnostic Commands**:
```bash
# Check directory permissions
ls -la ./configs/

# Test write permissions
python -c "open('test.txt', 'w').write('test')"
```

**Solutions**:
```bash
# Fix permissions
chmod -R 755 ./configs/
chmod -R 755 ./models/
```

### Model Loading Issues

**Problem**: Models not loading or errors during inference

**Diagnostic Commands**:
```python
# Python diagnostic script
import os
from paddleocr import PaddleOCR

ocr = PaddleOCR(engine="paddle")
result = ocr.predict("test.png")
print("Model loaded successfully!")
```

**Solutions**:
1. Check model download status
2. Verify model files integrity
3. Update PaddlePaddle to latest version
4. Check configuration files

## 2. Debugging Techniques

### Enable Debug Mode

```bash
# Enable debug logging
export PADDLE_OCR_DEBUG=True
python -m paddleocr ocr -i ./example.png --engine paddle

# Enable verbose output
python -m paddleocr ocr -i ./example.png --engine paddle --log-level DEBUG
```

### Python Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

from paddleocr import PaddleOCR

ocr = PaddleOCR(engine="paddle")

# Add debug prints
for i, result in enumerate(ocr.predict("example.png")):
    print(f"Result {i}: {result}")
    if 'error' in str(result):
        print(f"Error details: {result['error']}")
```

### Configuration Debug

```python
from paddleocr import PaddleOCR

# Print current configuration
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    engine="paddle",
)

print("Configuration:", ocr.config)
```

## 3. Performance Diagnostics

### Benchmark Tool Usage

```bash
# Basic benchmarking
python -m paddleocr.benchmark --engine paddle

# Detailed benchmarking
python -m paddleocr.benchmark --benchmark-detail --device gpu

# Multi-device benchmarking
python -m paddleocr.benchmark --device gpu,0,gpu,1
```

### Memory Usage Analysis

```python
import psutil
import paddle

def check_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"RAM Usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    if paddle.is_compiled_with_cuda():
        print(f"GPU Memory: {paddle.device.cuda.memory_allocated() / 1024 / 1024:.2f} MB")
```

### Speed Profiling

```python
import time
import cProfile
from paddleocr import PaddleOCR

ocr = PaddleOCR(engine="paddle")

# Profile performance
cProfile.run('ocr.predict("example.png")', 'profile_stats')
```

## 4. System Validation

### Quick Installation Check

```python
import paddle
import paddleocr

print("=== PaddleOCR Installation Check ===")
print(f"Python version: {sys.version}")
print(f"PaddlePaddle version: {paddle.__version__}")
print(f"PaddleOCR version: {paddleocr.__version__}")
print(f"CUDA support: {paddle.is_compiled_with_cuda()}")
print(f"GPU devices: {paddle.device.get_device()}")

# Quick OCR test
ocr = PaddleOCR(engine="paddle")
result = ocr.predict("general_ocr_002.png")
print("✓ OCR test passed!")
print("✓ Installation verified!")
```

### Model Integrity Check

```python
import os
from paddleocr import PaddleOCR

ocr = PaddleOCR(engine="paddle")

# Check critical files
required_dirs = [
    ".paddleocr/models",
    ".paddleocr/configs"
]

all_good = True
for dir_path in required_dirs:
    expanded = os.path.expanduser(dir_path)
    if os.path.exists(expanded):
        print(f"✓ {dir_path} exists")
        # List contents
        contents = os.listdir(expanded)
        print(f"  Contents: {', '.join(contents[:5])}")
    else:
        print(f"✗ {dir_path} missing")
        all_good = False

if all_good:
    print("\n✓ All checks passed!")
else:
    print("\n⚠ Some checks failed!")
```

### Hardware Compatibility

```bash
# Check supported hardware
python -c "
import paddle
print('CPU:', paddle.device.get_device())

if paddle.is_compiled_with_cuda():
    import torch
    print('GPU:', torch.cuda.get_device_name(0))
    print('CUDA version:', torch.version.cuda)
    print('GPU memory:', torch.cuda.get_device_properties(0).total_memory / 1024**3, 'GB')

print('CPU cores:', os.cpu_count())
"
```

## 5. Troubleshooting Checklist

| Check Item | Command | Expected Result |
|------------|---------|-----------------|
| Python version | `python --version` | 3.7+ |
| PaddlePaddle installation | `pip show paddlepaddle` | Success |
| GPU detection | `nvidia-smi` | GPU info displayed |
| PaddleOCR import | `python -c "import paddleocr; print(paddleocr.__version__)"` | Version printed |
| Model download | `ls ~/.paddleocr/models/` | Model files exist |
| Basic OCR test | Python OCR script | Text output |

## 6. Advanced Diagnostics

### Memory Leak Detection

```python
import paddle
import gc

# Monitor memory usage over time
for i in range(10):
    # Perform OCR
    ocr = PaddleOCR(engine="paddle")
    result = ocr.predict("example.png")
    
    # Force garbage collection
    gc.collect()
    
    # Clear GPU cache
    if paddle.is_compiled_with_cuda():
        paddle.device.cuda.empty_cache()
    
    # Check memory usage
    memory = paddle.device.cuda.memory_allocated()
    print(f"Iteration {i}: {memory / 1024 / 1024:.2f} MB")
```

### Model Loading Performance

```python
import time
from paddleocr import PaddleOCR

# Measure model loading time
start = time.time()
ocr = PaddleOCR(engine="paddle")
load_time = time.time() - start

print(f"Model loading time: {load_time:.3f}s")

# Measure inference time
start = time.time()
for _ in range(10):
    result = ocr.predict("example.png")
inf_time = time.time() - start

print(f"Average inference time: {inf_time / 10:.3f}s")
```

### Network Issues

```bash
# Test model download
python -m pip install --no-deps paddleocr --verbose

# Check network connectivity
curl -I https://www.paddlepaddle.org.cn

# Test download speed
time wget https://paddlepaddle.org.cn/models/test_model.zip
```

## 7. Emergency Procedures

### Reinstall from Scratch

```bash
# Remove PaddleOCR and reinstall
pip uninstall -y paddleocr
pip uninstall -y paddlepaddle
pip uninstall -y paddlepaddle-gpu
pip uninstall -y transformers

# Install fresh
pip install paddlepaddle==3.2.0
pip install "paddleocr[all]"
```

### Clear Cache
```bash
# Clear Python cache
rm -rf ~/.cache/pip
rm -rf ~/.local/share/pip
rm -rf ~/.paddleocr
rm -rf ~/.cache/torch
```

### Get Support

For assistance, check:
1. GitHub Issues: https://github.com/PaddlePaddle/PaddleOCR/issues
2. Official Forum: https://github.com/PaddlePaddle/PaddleOCR/discussions
3. Slack Channel: Join PaddlePaddle community
