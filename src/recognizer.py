import os
import numpy as np
import torch

try:
    import onnxruntime as ort
except Exception:
    ort = None

try:
    import easyocr
except Exception:
    easyocr = None


def apply_clahe(img_bgr):
    import cv2
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


class OCRRecognizer:
    def __init__(self, backend: str = "easyocr", langs=None, model_pt_path: str = None, model_onnx_path: str = None, device: str = "auto", use_onnx: bool = True, apply_clahe_opt: bool = True):
        if langs is None:
            langs = ["en"]
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.backend = backend
        self.apply_clahe_opt = apply_clahe_opt

        self.use_onnx = use_onnx and model_onnx_path and os.path.exists(model_onnx_path) and ort is not None
        self.ort_session = None
        self.reader = None

        if self.use_onnx:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if self.device == "cuda" else ["CPUExecutionProvider"]
            self.ort_session = ort.InferenceSession(model_onnx_path, providers=providers)
        else:
            if self.backend == "easyocr":
                if easyocr is None:
                    raise RuntimeError("easyocr not installed. Install or provide ONNX model.")
                gpu = self.device == "cuda"
                self.reader = easyocr.Reader(langs, gpu=gpu, verbose=False)
            else:
                # Placeholder for custom CRNN; for now fallback to EasyOCR if available
                if easyocr is None:
                    raise RuntimeError("CRNN backend not implemented; install easyocr or provide ONNX model.")
                gpu = self.device == "cuda"
                self.reader = easyocr.Reader(langs, gpu=gpu, verbose=False)

    def recognize(self, image_bgr: np.ndarray):
        import cv2
        crop = image_bgr
        
        if crop.size == 0:
            return "", 0.0
            
        # Fast preprocessing - resize to reasonable size
        h, w = crop.shape[:2]
        if h < 20 or w < 60:
            scale = max(20/h, 60/w)
            new_h, new_w = int(h * scale), int(w * scale)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)  # Better quality
        
        # Enhanced preprocessing for better letter detection (especially D vs 0/O)
        if self.apply_clahe_opt:
            crop = apply_clahe(crop)
        
        # Lightweight preprocessing to improve letter detection (fast, ~5-10ms)
        # Convert to grayscale for processing
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Light denoising (faster than fastNlMeansDenoising)
        # Use bilateral filter - preserves edges while reducing noise (~3-5ms)
        denoised = cv2.bilateralFilter(gray, 5, 50, 50)
        
        # Sharpen to make edges clearer (helps distinguish D from 0/O) (~1-2ms)
        kernel_sharpen = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
        
        # Enhance contrast (~2-3ms)
        clahe_gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe_gray.apply(sharpened)
        
        # Convert back to BGR for OCR (EasyOCR works better with color) (~0.5ms)
        crop = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        if self.ort_session is not None:
            # ONNX model processing
            img_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            img_resized = cv2.resize(img_gray, (160, 32))
            img_normalized = img_resized.astype(np.float32) / 255.0
            img_normalized = (img_normalized - 0.5) / 0.5
            img_input = img_normalized[None, None, :, :]
            
            outputs = self.ort_session.run(None, {self.ort_session.get_inputs()[0].name: img_input})
            text = str(outputs[0][0]) if len(outputs) > 0 else ""
            conf = float(outputs[1][0]) if len(outputs) > 1 else 0.0
            return text, conf
        else:
            # Enhanced EasyOCR processing with better settings for letter detection
            # Try multiple passes with different settings to catch tricky letters like W
            results = []
            
            # Pass 1: Standard settings
            result1 = self.reader.readtext(
                crop, 
                detail=1, 
                paragraph=False, 
                contrast_ths=0.1,
                text_threshold=0.3,
                low_text=0.3,
                link_threshold=0.3,
                width_ths=0.5,
                height_ths=0.5,
                mag_ratio=1.5,
                min_size=10,
                allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            )
            if result1:
                results.extend(result1)
            
            # Pass 2: Even more lenient for catching W (which is often missed)
            result2 = self.reader.readtext(
                crop,
                detail=1,
                paragraph=False,
                contrast_ths=0.05,  # Very low for faint W
                text_threshold=0.2,  # Very low
                low_text=0.2,
                link_threshold=0.2,
                width_ths=0.3,  # Very lenient
                height_ths=0.3,
                mag_ratio=2.0,  # Scale up more
                min_size=8,  # Detect even smaller
                allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            )
            if result2:
                results.extend(result2)
            
            if not results:
                return "", 0.0
            
            # Return the best result (highest confidence)
            best = max(results, key=lambda r: r[2])
            text = best[1].strip()
            conf = float(best[2])
            
            # Only return if it looks like a license plate
            if len(text) >= 4 and conf > 0.3:
                return text, conf
            return "", 0.0


