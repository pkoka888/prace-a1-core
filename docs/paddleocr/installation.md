# Installation Guide

> **Historical reference — do not execute or install from this document.** The
> active OCR stack must be selected and pinned through current architecture proofs.

## 1. CPU Installation (Recommended)

To install PaddleOCR with CPU support only:

```bash
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install "paddleocr\[all\]"
```

## 2. GPU Installation

### Linux with NVIDIA GPU

For CUDA 11.8:

```bash
python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
python -m pip install "paddleocr\[all\]"
```

For newer CUDA versions, check the [official installation guide](https://www.paddlepaddle.org.cn/install/quick).

## 3. Transformers backend

```bash
python -m pip install "transformers>=5.8.0"
python -m pip install "paddleocr\[all\]"
```

> **Note**: When using the Transformers backend, you may need to install additional backends like OpenVINO, ONNX Runtime, or TensorRT depending on your deployment scenario.

## 4. Conda Installation

```bash
conda install -c paddlepaddle paddleocr
```

## 5. Development Installation

To install from source:

```bash
git clone https://github.com/PaddlePaddle/PaddleOCR.git
cd PaddleOCR
pip install -r requirements.txt
python setup.py install
```

## 6. Docker Deployment

```bash
docker pull paddlepaddle/paddleocr:latest
docker run -it paddlepaddle/paddleocr:latest
```

## 7. PyPI Installation

```bash
pip install paddleocr
```
