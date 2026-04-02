"""
comfyui_regional.py - ComfyUI + Regional Prompter 다중 캐릭터 이미지 생성

설치:
  1. https://github.com/comfyanonymous/ComfyUI
  2. cd ComfyUI/custom_nodes && git clone https://github.com/hako-mikan/sd-webui-regional-prompter
  3. 모델: ComfyUI/models/checkpoints/ 에 .safetensors 배치 (Anything V5 추천)
  4. python main.py --listen
"""
import io, os, requests
from PIL import Image

COMFYUI_URL = "http://127.0.0.1:8188"


def is_comfyui_available():
    try: return requests.get(f"{COMFYUI_URL}/system_stats", timeout=3).status_code == 200
    except: return False

def list_available_models():
    try:
        r = requests.get(f"{COMFYUI_URL}/object_info/CheckpointLoaderSimple", timeout=5)
        return r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except: return []


def _build_workflow(prompt_left, prompt_right, base_prompt, negative_prompt, seed,
                    width=768, height=1344, checkpoint="AnythingV5_v5PrtRE.safetensors",
                    split_ratio="1,1", steps=28, cfg=7.0):
    """
    Regional Prompter 워크플로
    ┌────────┬────────┐
    │ 왼쪽 A  │ 오른쪽 B │  split_ratio: "1,1"=50:50
    └────────┴────────┘
    """
    text = f"{base_prompt} ADDBASE {prompt_left} ADDROW {prompt_right}"
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "RegionalPrompter", "inputs": {
            "mode": "Columns", "debug": False, "save_mask": False,
            "prompt": ["2", 0], "base_ratios": "0.2", "ratios": split_ratio,
            "use_base": True, "use_common": False, "use_N_X_prompt": False,
            "latent": ["4", 0], "model": ["1", 0], "clip": ["1", 1],
        }},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["5", 0], "positive": ["5", 1], "negative": ["3", 0],
            "latent_image": ["5", 2], "seed": seed, "steps": steps,
            "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "regional_"}}
    }


def _submit(workflow):
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=10)
    r.raise_for_status()
    return r.json()["prompt_id"]


def _wait(prompt_id, timeout=300):
    import time
    print(f"   ⏳ ComfyUI 생성 중 (최대 {timeout}초)...")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10).json()
        if prompt_id not in history: continue
        for _, out in history[prompt_id].get("outputs", {}).items():
            if "images" in out:
                info = out["images"][0]
                r = requests.get(f"{COMFYUI_URL}/view",
                    params={"filename": info["filename"], "subfolder": info.get("subfolder", ""), "type": info.get("type", "output")},
                    timeout=30)
                return Image.open(io.BytesIO(r.content))
    raise TimeoutError(f"ComfyUI 타임아웃 ({timeout}초)")


def generate_regional(prompt_left, prompt_right,
                      base_prompt="masterpiece, best quality, anime style",
                      negative_prompt="worst quality, low quality, blurry, deformed, extra limbs",
                      seed=42, split_ratio="1,1", checkpoint=None,
                      save_path="output_regional.png", width=768, height=1344):
    """두 캐릭터를 좌/우 영역에 각각 생성"""
    if not is_comfyui_available():
        raise ConnectionError(f"ComfyUI 연결 실패. 실행: python main.py --listen ({COMFYUI_URL})")
    if checkpoint is None:
        models = list_available_models()
        if not models: raise RuntimeError("ComfyUI에 로드된 모델 없음")
        checkpoint = models[0]
        print(f"   🔍 모델: {checkpoint}")
    img = _wait(_submit(_build_workflow(prompt_left, prompt_right, base_prompt, negative_prompt,
                                        seed, width, height, checkpoint, split_ratio)))
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    img.save(save_path, "PNG")
    print(f"   ✅ Regional 저장: {save_path}")
    return save_path


def generate_over_the_shoulder(back_prompt, front_prompt,
                               base_prompt="masterpiece, best quality, anime style, cinematic",
                               negative_prompt="worst quality, low quality, blurry, deformed",
                               seed=42, save_path="output_ots.png"):
    """
    Over-the-shoulder: 뒷모습(좌 33%) + 정면(우 67%)
    """
    return generate_regional(
        prompt_left=f"back view, from behind, {back_prompt}, blurred slightly",
        prompt_right=f"{front_prompt}, facing viewer, emotional expression, sharp focus",
        base_prompt=base_prompt, negative_prompt=negative_prompt,
        seed=seed, split_ratio="1,2", save_path=save_path,
    )
