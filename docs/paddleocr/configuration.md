# Configuration Guide

> **Historical reference — do not execute.** No active repository workflow uses
> this configuration as authority.

## 1. Configuration Files

PaddleOCR uses YAML configuration files stored in the `configs/` directory:

### PP-OCRv6 Configuration
- File: `configs/pp_ocr_v6/mode_choice.yml`
- Purpose: Model selection and common settings

### PP-StructureV3 Configuration
- File: `configs/pp_structure_v3/layout_detection.yml`
- Purpose: Document layout detection settings

### PaddleOCR-VL Configuration
- File: `configs/ppocr_vl/config.yml`
- Purpose: Vision-language model configuration

## 2. Key Configuration Parameters

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| `use_doc_orientation_classify` | Enable text orientation classification | `true` / `false` |
| `use_doc_unwarping` | Enable document unwarping | `true` / `false` |
| `use_textline_orientation` | Enable text line orientation detection | `true` / `false` |
| `engine` | Backend engine | `paddle` / `transformers` |
| `use_formula_recognition` | Enable formula recognition | `true` / `false` |
| `wireless_table_structure_recognition_model_name` | Table structure recognition model | `SLANeXt_wireless` |

## 3. Environment Variables

Set environment variables to configure global behavior:

```bash
# Set precision to fp16 for faster inference
export PADDLE_PRECISION=fp16

# Restrict GPU usage
export CUDA_VISIBLE_DEVICES=0,1,2

# Customize log level
export PADDLE_OCR_LOG_LEVEL=DEBUG

# Set data directory for benchmarking
export PADDLE_OCR_EVAL_DATA_DIR=/path/to/evaluation/data
```

## 4. Model Paths and Sources

PaddleOCR supports multiple model sources:

1. **Official Website Models**
   ```
   https://www.paddleocr.com
   ```

2. **HuggingFace Models**
   ```
   https://huggingface.co/collections/PaddlePaddle/pp-ocrv6
   ```

3. **ModelScope**
   ```
   https://www.modelscope.cn/collections/PaddlePaddle/PP-OCRv6
   ```

## 5. Advanced Configuration

### Multi-GPU Support
```bash
export CUDA_VISIBLE_DEVICES=0,1
export PADDLE_USE_DISTRIBUTED=True
```

### Mixed Precision Training
```bash
export PADDLE_MASTER_BATCH_ENC=True
export PADDLE_MASTER_BATCH_DEC=True
export PADDLE_CUDNN_LIMIT_MAX_BATCH_SIZE=200
```

### Custom Model Loading
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    model_dir="./custom_model_path",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    engine="paddle"
)
