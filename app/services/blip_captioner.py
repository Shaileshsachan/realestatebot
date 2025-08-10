from typing import Optional
from io import BytesIO
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

_blip_processor: Optional[BlipProcessor] = None
_blip_model: Optional[BlipForConditionalGeneration] = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def _ensure_blip_loaded():
    global _blip_processor, _blip_model
    if _blip_processor is None or _blip_model is None:
        _blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(_device)

def caption_image_bytes(image_bytes: bytes) -> str:
    _ensure_blip_loaded()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = _blip_processor(image, return_tensors="pt").to(_device)
    with torch.no_grad():
        out = _blip_model.generate(**inputs, max_new_tokens=40)
    caption = _blip_processor.decode(out[0], skip_special_tokens=True)
    return caption
