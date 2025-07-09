import torch
# Monkey-patch torch.load to disable weights_only default in PyTorch 2.6+
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from styletts2 import tts as styletts
import os
import logging
import signal
import torch.serialization
import torch.optim

app = FastAPI(title="StyleTTS2 TTS API")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix for PyTorch 2.6+ loading issue with style-tts-2 checkpoints
# The model checkpoint uses classes that are not allowed by default with `weights_only=True`.
torch.serialization.add_safe_globals([getattr, torch.optim.lr_scheduler.OneCycleLR])

# Detect device
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
logger.info(f"Using device: {device}")

# Load model at startup
logger.info("Loading StyleTTS2 model...")
# The paths are relative to the StyleTTS2 directory.
model = styletts.StyleTTS2(
    model_checkpoint_path='StyleTTS2-LibriTTS/Models/LibriTTS/epoch_2nd_00012.pth', 
    config_path='StyleTTS2-LibriTTS/Models/LibriTTS/config_vokan.yml'
)
logger.info("StyleTTS2 model loaded.")


# Define request model
class TTSRequest(BaseModel):
    text: str
    target_voice_path: str
    output_wav_file: str
    diffusion_steps: int = 30

@app.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    try:
        logger.info(f"Generating audio for text: '{request.text}'")
        
        if not os.path.exists(request.target_voice_path):
            raise HTTPException(status_code=400, detail=f"Target voice file not found at {request.target_voice_path}")

        text = request.text
        if text and text[-1] not in ['.', '!', '?', ',']:
            text += "."
            
        model.inference(
            text,
            target_voice_path=request.target_voice_path,
            output_wav_file=request.output_wav_file,
            diffusion_steps=request.diffusion_steps
        )
        
        if not os.path.exists(request.output_wav_file) or os.path.getsize(request.output_wav_file) == 0:
            raise HTTPException(status_code=500, detail="TTS generation failed to produce an output file.")
            
        return {"status": "success", "message": f"Audio saved to {request.output_wav_file}"}
    
    except Exception as e:
        logger.error(f"Error generating audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")

@app.post("/shutdown")
async def shutdown():
    logger.info("Shutdown request received")
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutdown", "message": "Server shutting down"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013) 