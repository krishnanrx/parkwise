import os
import torch
import numpy as np

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

try:
    import onnxruntime as ort
except Exception:
    ort = None


class PlateDetector:
    def __init__(self, model_pt_path: str, model_onnx_path: str = None, device: str = "auto", conf_threshold: float = 0.5, iou_threshold: float = 0.5, input_size: int = 640, use_onnx: bool = True):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.use_onnx = use_onnx and model_onnx_path and os.path.exists(model_onnx_path) and ort is not None

        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        if self.use_onnx:
            providers = [
                ("CUDAExecutionProvider", {"arena_extend_strategy": "kNextPowerOfTwo"}),
                "CPUExecutionProvider",
            ] if self.device == "cuda" else ["CPUExecutionProvider"]
            self.ort_session = ort.InferenceSession(model_onnx_path, providers=providers)
            self.yolo = None
        else:
            if YOLO is None:
                raise RuntimeError("Ultralytics YOLO not available and no ONNX model provided")
            self.yolo = YOLO(model_pt_path)
            self.yolo.fuse()
            self.ort_session = None

    def _preprocess(self, image_bgr: np.ndarray) -> np.ndarray:
        import cv2
        img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        scale = self.input_size / max(h, w)
        nh, nw = int(h * scale), int(w * scale)
        resized = cv2.resize(img, (nw, nh))
        padded = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        padded[:nh, :nw] = resized
        padded = padded.astype(np.float32) / 255.0
        padded = padded.transpose(2, 0, 1)[None]
        return padded, scale

    def detect(self, image_bgr: np.ndarray):
        if self.use_onnx:
            blob, scale = self._preprocess(image_bgr)
            outputs = self.ort_session.run(None, {self.ort_session.get_inputs()[0].name: blob})
            preds = outputs[0]
            boxes, scores = self._postprocess_yolo_like(preds, image_bgr.shape, scale)
            return boxes, scores
        else:
            # Use smaller input size for speed
            results = self.yolo.predict(
                source=image_bgr, 
                imgsz=416,  # Smaller for speed
                conf=self.conf_threshold, 
                iou=self.iou_threshold, 
                verbose=False, 
                device=0 if self.device == "cuda" else None,
                half=True if self.device == "cuda" else False  # Use FP16 for speed
            )
            boxes = []
            scores = []
            # COCO class IDs for cars and motorcycles only
            vehicle_classes = [2, 3]  # car=2, motorcycle=3
            for r in results:
                if r.boxes is None:
                    continue
                for b in r.boxes:
                    xyxy = b.xyxy[0].cpu().numpy().tolist()
                    conf = float(b.conf[0].cpu().numpy())
                    cls = int(b.cls[0].cpu().numpy()) if hasattr(b, 'cls') else 0
                    # Only detect vehicles
                    if conf >= self.conf_threshold and cls in vehicle_classes:
                        x1, y1, x2, y2 = xyxy
                        h = y2 - y1
                        w = x2 - x1
                        
                        # Different logic for cars vs motorcycles
                        if cls == 3:  # Motorcycle - use full bounding box
                            plate_box = [
                                max(0, x1),
                                max(0, y1),  # Full height for bikes
                                min(image_bgr.shape[1], x2),
                                min(image_bgr.shape[0], y2)
                            ]
                        else:  # Car (class 2) - use lower 25%
                            plate_box = [
                                max(0, x1),
                                max(0, y1 + h*0.75),  # Lower 25% of vehicle
                                min(image_bgr.shape[1], x2),
                                min(image_bgr.shape[0], y2)
                            ]
                        boxes.append(plate_box)
                        scores.append(conf)
            return boxes, scores

    def _postprocess_yolo_like(self, preds: np.ndarray, shape, scale: float):
        # This method expects YOLO-style output (N, num_boxes, 85) -> adapt per model
        # For portability, assume boxes already filtered. If custom ONNX, adjust decoding.
        # Here we treat preds as [num, 6] -> x1,y1,x2,y2,conf,cls
        h, w = shape[:2]
        boxes = []
        scores = []
        if preds.ndim == 3:
            preds = preds[0]
        for row in preds:
            if len(row) < 6:
                continue
            x1, y1, x2, y2, conf, cls = row[:6]
            if conf < self.conf_threshold:
                continue
            # Undo letterbox scaling
            inv = 1.0 / scale
            x1 = float(np.clip(x1 * inv, 0, w - 1))
            y1 = float(np.clip(y1 * inv, 0, h - 1))
            x2 = float(np.clip(x2 * inv, 0, w - 1))
            y2 = float(np.clip(y2 * inv, 0, h - 1))
            boxes.append([x1, y1, x2, y2])
            scores.append(float(conf))
        return boxes, scores
