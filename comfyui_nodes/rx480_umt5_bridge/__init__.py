"""ComfyUI custom node: Wan UMT5 embeddings from a LOCAL llama.cpp server.

Tested architecture: t5encoder, UMT5-XXL GGUF Q5_K_M, llama.cpp patched
encoder-only server with llama_encode(), RX 480 Vulkan /embeddings API.
"""

import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

import torch


class RX480UMT5WanBridge:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "default": "A futuristic android walking through a neon-lit city."}),
                "server_url": ("STRING", {"default": "http://127.0.0.1:8089"}),
                "pad_to": ("INT", {"default": 512, "min": 0, "max": 512, "step": 1}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "encode"
    CATEGORY = "conditioning/wan"
    DESCRIPTION = "UMT5 GGUF on RX 480 via local patched llama.cpp /embeddings; returns Wan CONDITIONING."

    def encode(self, text, server_url, pad_to):
        base = server_url.strip().rstrip("/")
        parsed = urlparse(base)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Per sicurezza il server deve essere http://127.0.0.1:8089 (o localhost con una porta locale).")

        body = json.dumps({"content": text, "embd_normalize": -1}).encode("utf-8")
        request = urllib.request.Request(
            base + "/embeddings",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as reply:
                response = json.load(reply)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                f"Server UMT5 non raggiungibile all'indirizzo {base}: {exc}. "
                "Avvia Start-UMT5-RX480.ps1 e verifica che sia sulla RX 480."
            ) from exc

        if not isinstance(response, list) or len(response) != 1 or not isinstance(response[0], dict):
            raise RuntimeError("Risposta /embeddings inattesa: serve una lista con un elemento per il singolo prompt.")
        raw = response[0].get("embedding")
        if not isinstance(raw, list) or not raw:
            raise RuntimeError("La risposta del server non contiene embedding per token.")

        try:
            vectors = torch.tensor(raw, dtype=torch.float32, device="cpu")
        except (TypeError, ValueError, RuntimeError) as exc:
            raise RuntimeError("Embedding restituiti dal server non convertibili in float32.") from exc

        if vectors.ndim != 2 or vectors.shape[1] != 4096:
            raise RuntimeError(f"UMT5 Wan richiede embedding [N,4096], ricevuto {tuple(vectors.shape)}.")
        n_tokens = vectors.shape[0]
        if n_tokens > 512:
            raise ValueError(f"Prompt troppo lungo per il contesto UMT5 del server: {n_tokens} token > 512.")
        if not bool(torch.isfinite(vectors).all()):
            raise RuntimeError("Il server ha restituito NaN/Inf: conditioning non valido.")

        # Wan vanilla CLIP Text Encode pads UMT5 to 512 with zeroed positions.
        target = max(n_tokens, int(pad_to))
        if target > n_tokens:
            out = torch.zeros((1, target, 4096), dtype=torch.float32, device="cpu")
            out[0, :n_tokens, :] = vectors
        else:
            out = vectors.unsqueeze(0).contiguous()

        print(f"[RX480 UMT5 Bridge] {n_tokens} token validi -> CONDITIONING {tuple(out.shape)}; server={base}", flush=True)
        return ([[out, {"pooled_output": None}]],)


NODE_CLASS_MAPPINGS = {"RX480UMT5WanBridge": RX480UMT5WanBridge}
NODE_DISPLAY_NAME_MAPPINGS = {"RX480UMT5WanBridge": "RX480 UMT5 Wan Bridge"}
