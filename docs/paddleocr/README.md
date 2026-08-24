---
status: historical
superseded_by: requirements.txt (rapidocr==3.9.2), scripts/ (local OCR pipeline)
date: 2026-08-11
note: "Historical reference — PaddleOCR evaluation superseded by RapidOCR local-first pipeline. Do not execute."
---

# PaddleOCR Documentation

> **Historical reference — do not execute.** The described PaddleOCR workflow is
> not present in the active repository. Current OCR selection and implementation
> are governed by Plans E, N, and O after synthetic proofs.

This directory contains comprehensive documentation for installing, using, configuring, testing, and diagnosing PaddleOCR.

## Overview

PaddleOCR is a powerful, lightweight OCR toolkit that bridges the gap between images/PDFs and LLMs. It supports 100+ languages and is built on the PaddlePaddle and Hugging Face Transformers frameworks.

## Installation Methods

### Method 1: pip (Recommended)

#### CPU Installation
```bash
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

#### GPU Installation (Linux with CUDA 11.8)
```bash
python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
```

#### With Full Functionality
```bash
python -m pip install "paddleocr\[all\]"
```

#### Transformers Backend
```bash
python -m pip install "transformers>=5.8.0"
```

### Method 2: Conda
```bash
conda install -c paddlepaddle paddleocr
```

### Method 3: Build from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/PaddlePaddle/PaddleOCR.git
   cd PaddleOCR
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Build and install:
   ```bash
   python setup.py install
   ```

### Method 4: Docker
```bash
docker pull paddlepaddle/paddleocr:latest
docker run -it paddlepaddle/paddleocr:latest
```

### Method 5: PyPI
```bash
pip install paddleocr
```

## Usage

### CLI Usage

#### OCR Detection
```bash
# Using PaddlePaddle engine
paddleocr ocr -i ./example.png --engine paddle

# Using Transformers engine
paddleocr ocr -i ./example.png --engine transformers
```

#### Text Detection
```bash
paddleocr text_detection -i ./example.png --engine paddle
paddleocr text_detection -i ./example.png --engine transformers
```

#### Text Recognition
```bash
paddleocr text_recognition -i ./example.png --engine paddle
paddleocr text_recognition -i ./example.png --engine transformers
```

#### Structure Detection
```bash
paddleocr pp_structurev3 -i ./pp_structure_v3_demo.png --engine paddle
paddleocr pp_structurev3 -i ./pp_structure_v3_demo.png --engine transformers
```

### Python API

#### Basic OCR
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    engine="paddle",
)
result = ocr.predict("./example.png")
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")
```

#### Transformers Backend
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    engine="transformers",
)
result = ocr.predict("./example.png")
```

#### Text Detection
```python
from paddleocr import TextDetection

model = TextDetection(engine="paddle")
output = model.predict("example.png")
for res in output:
    res.print()
```

#### Text Recognition
```python
from paddleocr import TextRecognition

model = TextRecognition(engine="paddle")
result = model.predict(input="example.png")
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")
```

#### Structure Detection
```python
from paddleocr import PPStructureV3

pipeline = PPStructureV3(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    engine="paddle",
)
output = pipeline.predict(input="./pp_structure_v3_demo.png")
for res in output:
    res.print()
    res.save_to_json(save_path="output")
    res.save_to_markdown(save_path="output")
```

## Configuration

### Configuration Files

PaddleOCR uses configuration files in the `configs/` directory:

- **PP-OCRv5**: `configs/pp_ocr_v5/`
- **PP-OCRv6**: `configs/pp_ocr_v6/`
- **PP-StructureV3**: `configs/pp_structure_v3/`
- **PaddleOCR-VL**: `configs/ppocr_vl/`

### Environment Variables

```bash
export PADDLE_PRECISION=fp16
export CUDA_VISIBLE_DEVICES=0,1,2
export PADDLE_OCR_EVAL_DATA_DIR=/path/to/data
```

### Model Paths

- **Pretrained models**: `https://paddleocr.com`
- **HuggingFace models**: https://huggingface.co/collections/PaddlePaddle
- **ModelScope**: https://www.modelscope.cn

## Testing

### Running Unit Tests
```bash
cd paddleocr
python -m pytest tests/ -v
```

### Benchmarking
```bash
python -m paddleocr.benchmark --engine paddle
```

### Manual Testing
1. Install PaddleOCR:
   ```bash
   python -m pip install paddleocr
   ```
2. Run the demo:
   ```bash
   paddleocr ocr -i ./demo.png --engine paddle
   ```

## Diagnostics

### Common Issues

1. **Installation fails**:
   - Check Python version: `python --version`
   - Verify CUDA version: `nvcc --version`
   - Check pip version: `pip --version`

2. **GPU not detected**:
   ```bash
   nvidia-smi
   python -c "import paddle; print(paddle.is_compiled_with_cuda())"
   ```

3. **Permission errors**:
   ```bash
   ls -la configs/
   ```

4. **Module not found**:
   ```bash
   python -c "import paddleocr; print(paddleocr.__version__)"
   ```

5. **Performance issues**:
   - Check GPU memory: `nvidia-smi`
   - Reduce batch size
   - Use CPU mode for testing

### Debug Mode
```bash
export PADDLE_OCR_DEBUG=True
python -m paddleocr ocr -i ./example.png
```

### Logs
```bash
python -m paddleocr ocr -i ./example.png --engine paddle --log-level DEBUG
```

## References

- **Official Website**: [https://www.paddleocr.com](https://www.paddleocr.com)
- **GitHub**: https://github.com/PaddlePaddle/PaddleOCR
- **Documentation**: https://paddleocr.ai
- **HPD-Parsing Tutorial**: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/HPD-Parsing.html

## Quick Start

1. Install PaddleOCR:
   ```bash
   python -m pip install paddleocr
   ```

2. Run OCR:
   ```bash
   paddleocr ocr -i ./example.png --engine paddle
   ```

3. Use Python API:
   ```python
   from paddleocr import PaddleOCR
   ocr = PaddleOCR(engine="paddle")
   result = ocr.predict("example.png")
   ```

## License

Apache 2.0 License

## Citation

Please cite PaddleOCR as:
```
@article{cui2025paddleocr30technicalreport,
      title={PaddleOCR 3.0 Technical Report},
      author={Cui, Cheng and Sun, Ting and Lin, Manhui and others},
      year={2025},
      eprint={2507.05595},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2507.05595}
}
```
