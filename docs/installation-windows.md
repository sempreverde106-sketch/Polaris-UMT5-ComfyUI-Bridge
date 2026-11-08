# Windows Installation Guide

## Status

Experimental. Successfully tested with an AMD Radeon RX 480 8GB on Windows 11.

The Vulkan and encoder patches have passed git apply checks against
llama.cpp commit 55ac0909e. A complete installation from this guide
has not yet been independently validated.

## 1. Requirements

- Windows 11 (tested)
- AMD GPU with a functioning Vulkan driver
- Git
- CMake (tested: 4.4.4)
- Visual Studio 2022 with Desktop development with C++
- LunarG Vulkan SDK (tested: 1.4.363.1)
- UMT5-XXL GGUF encoder model
- ComfyUI with PyTorch

Other Polaris GPUs are not yet confirmed compatible.

## 2. Obtain the project

Open **Windows PowerShell** in the folder where you want to keep both repositories.

Clone this project:

```powershell
git clone https://github.com/sempreverde106-sketch/Polaris-UMT5-ComfyUI-Bridge.git
```

> While this repository is private, cloning requires authorized GitHub access.

Clone upstream llama.cpp:

```powershell
git clone https://github.com/ggml-org/llama.cpp.git
```

Checkout the **exact tested revision**:

```powershell
git -C llama.cpp checkout 55ac0909e
```

## 3. Apply the patches

Run these commands from the **parent directory** containing both repositories.

Check both patches **without applying changes**:

```powershell
git -C llama.cpp apply --check ../Polaris-UMT5-ComfyUI-Bridge/patches/polaris-vulkan.patch
git -C llama.cpp apply --check ../Polaris-UMT5-ComfyUI-Bridge/patches/umt5-server-encoder.patch
```

Both checks must finish without an error. Then apply them:

```powershell
git -C llama.cpp apply ../Polaris-UMT5-ComfyUI-Bridge/patches/polaris-vulkan.patch
git -C llama.cpp apply ../Polaris-UMT5-ComfyUI-Bridge/patches/umt5-server-encoder.patch
```

Confirm only the expected upstream source files changed:

```powershell
git -C llama.cpp diff --stat
```

Expected modified files: `ggml/src/ggml-vulkan/ggml-vulkan.cpp` and `tools/server/server-context.cpp`.

## 4. Build llama.cpp with Vulkan

Run from the **parent directory** containing the `llama.cpp` folder, with Visual Studio's C++ workload and the Vulkan SDK installed:

```powershell
cmake -S llama.cpp -B llama.cpp/build-polaris -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DLLAMA_BUILD_SERVER=ON
```

Build the server:

```powershell
cmake --build llama.cpp/build-polaris --config Release --target llama-server --parallel 4
```

Check the executable (its dependencies are in the build output as well):

```powershell
& ".\llama.cpp\build-polaris\bin\Release\llama-server.exe" --version
```

Expected executable: `llama.cpp/build-polaris/bin/Release/llama-server.exe`.

If CMake cannot find Vulkan, verify that the Vulkan SDK is installed
and the VULKAN_SDK environment variable is configured.

## 5. Select the Vulkan GPU

Check the Vulkan devices reported by the patched server and its startup logs.

On the tested computer:

- `Vulkan0` = Radeon RX 6950 XT
- `Vulkan1` = Radeon RX 480

Device numbering is **system-dependent**. Do not assume that `Vulkan1` is the Polaris GPU on another computer; confirm the device name before loading the model.

## 6. Start the UMT5 server

Download the UMT5-XXL GGUF model separately from [city96 on Hugging Face](https://huggingface.co/city96/umt5-xxl-encoder-gguf). The tested file is `umt5-xxl-encoder-Q5_K_M.gguf`; model weights are **not included** here.

Use `scripts/Start-UMT5-Polaris.ps1` from the **project repository root**. Replace the example paths with the actual locations on your computer:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\Start-UMT5-Polaris.ps1" -ServerExe "C:\path\to\llama-server.exe" -ModelPath "C:\path\to\umt5-xxl-encoder-Q5_K_M.gguf" -Device Vulkan1 -GpuLayers 12
```

Leave the server console running. By default it listens **only on localhost**, at `http://127.0.0.1:8089`.

Tested server settings:
- GPU layers: 12
- Context: 512
- Batch size: 256
- Microbatch size: 256
- Embeddings enabled
- Pooling: none
- One parallel request

Do not expose the server to the public internet.

## 7. Install the ComfyUI node

Copy the folder `comfyui_nodes/rx480_umt5_bridge` into your ComfyUI `custom_nodes` directory, then restart ComfyUI.

Search for the node named **RX480 UMT5 Wan Bridge**.

Use one instance for positive conditioning and another for negative conditioning when required by your workflow.

- Default server URL: `http://127.0.0.1:8089`
- Default padding: `512` tokens
- Expected output using default padding: `CONDITIONING` containing a float32 tensor of shape `[1, 512, 4096]` for prompts up to 512 tokens.

Disconnect the normal UMT5 conditioning nodes when testing the bridge; keep the rest of the workflow identical for comparisons.

## 8. Smoke test: embedding response

With the server running on port `8089`, open **another PowerShell window** and send a short, known test prompt:

```powershell
$body = @{
    content = 'A futuristic android walking through a neon-lit city.'
    embd_normalize = -1
} | ConvertTo-Json -Compress

$r = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8089/embeddings' -ContentType 'application/json' -Body $body -TimeoutSec 180

$tokens = $r[0].embedding.Count
$dims = $r[0].embedding[0].Count

if ($tokens -ne 13 -or $dims -ne 4096) {
    throw "Unexpected result: $tokens tokens x $dims dimensions"
}

Write-Host "OK: $tokens tokens x $dims dimensions" -ForegroundColor Green
```

Expected: `OK: 13 tokens x 4096 dimensions` with the tested model and prompt. This only checks the **shape**, not numerical accuracy or long-term stability.

## 9. Verified results

Tested with UMT5-XXL Q5_K_M on an RX 480 8GB.

- 10 consecutive embedding requests completed at 12 GPU layers.
- Mean cosine similarity vs CPU reference: 0.99951431.
- Two consecutive Wan 2.2 videos generated correctly.
- Total time for two videos: 228.41 seconds.
- Standard encoder comparison: 347.02 seconds.
- Observed reduction: approximately 34.2%.

These are measurements from a single system and workflow.

## 10. Known limitations

- The Vulkan patch modifies device creation and queue selection in llama.cpp; it is experimental and may affect **other Vulkan GPUs**, not just Polaris. Use a separate build and verify the selected device before testing.
- Comments in the patch mention RX 570, but **only RX 480 8GB has been validated** in this project.
- Offloading 25 or more GPU layers caused Vulkan ErrorDeviceLost
  during repeated long-prompt tests on the RX 480.
- 12 and 24 layers passed the tested repeated-request sequence.
- System RAM usage remains high during Wan High/Low model switching.
- Other Polaris models, driver versions and operating systems
  require independent testing.
- Model files are not distributed in this repository.

## 11. Troubleshooting

If the server does not start:
- Verify the model path.
- Verify the selected Vulkan device.
- Verify that no other application is using port 8089.
- Check that Vulkan SDK and drivers are installed correctly.

If ComfyUI cannot connect:
- Check that the server is still running.
- Confirm that the node URL is http://127.0.0.1:8089.
- Verify that the patched llama.cpp server supports encoder embeddings.

If Vulkan reports ErrorDeviceLost:
- Return to the tested 12-layer configuration.
- Avoid assuming that full-model GPU offloading is stable.
- Record the GPU model, driver, prompt length and error logs.