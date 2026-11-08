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

Clone this repository:

git clone https://github.com/sempreverde106-sketch/Polaris-UMT5-ComfyUI-Bridge.git

Clone llama.cpp:

git clone https://github.com/ggml-org/llama.cpp.git

Checkout the tested llama.cpp revision:

git -C llama.cpp checkout 55ac0909e

## 3. Apply the patches

Run these commands from the directory containing both repositories:

git -C llama.cpp apply --check Polaris-UMT5-ComfyUI-Bridge/patches/polaris-vulkan.patch

git -C llama.cpp apply --check Polaris-UMT5-ComfyUI-Bridge/patches/umt5-server-encoder.patch

Both checks must succeed before proceeding.

Apply the patches:

git -C llama.cpp apply Polaris-UMT5-ComfyUI-Bridge/patches/polaris-vulkan.patch

git -C llama.cpp apply Polaris-UMT5-ComfyUI-Bridge/patches/umt5-server-encoder.patch

## 4. Build llama.cpp with Vulkan

Run from the directory containing the llama.cpp folder:

cmake -S llama.cpp -B llama.cpp/build-polaris -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DLLAMA_BUILD_SERVER=ON

cmake --build llama.cpp/build-polaris --config Release --target llama-server

Expected executable:

llama.cpp/build-polaris/bin/Release/llama-server.exe

If CMake cannot find Vulkan, verify that the Vulkan SDK is installed
and the VULKAN_SDK environment variable is configured.

## 5. Select the Vulkan GPU

Check the Vulkan devices reported by llama.cpp.

On the tested computer:

Vulkan0 = Radeon RX 6950 XT
Vulkan1 = Radeon RX 480

Device numbering is system-dependent.
Do not assume that Vulkan1 is the Polaris GPU on another computer.

## 6. Start the UMT5 server

Use scripts/Start-UMT5-Polaris.ps1.

Example from the project root:

powershell.exe -ExecutionPolicy Bypass -File ".\scripts\Start-UMT5-Polaris.ps1" -ServerExe "C:\path\to\llama-server.exe" -ModelPath "C:\path\to\umt5-xxl-encoder-Q5_K_M.gguf" -Device Vulkan1 -GpuLayers 12

Replace the example paths and device with the correct values.

The server listens on 127.0.0.1:8089.

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

Copy:

comfyui_nodes/rx480_umt5_bridge

into the ComfyUI custom_nodes directory.

Restart ComfyUI.

Find the node:

RX480 UMT5 Wan Bridge

Use one instance for positive conditioning and another for negative
conditioning when required by the workflow.

Default server URL:

http://127.0.0.1:8089

Default padding:

512 tokens

The node returns CONDITIONING containing a float32 tensor
with shape [1, 512, 4096] when using the default padding.

## 8. Verified results

Tested with UMT5-XXL Q5_K_M on an RX 480 8GB.

- 10 consecutive embedding requests completed at 12 GPU layers.
- Mean cosine similarity vs CPU reference: 0.99951431.
- Two consecutive Wan 2.2 videos generated correctly.
- Total time for two videos: 228.41 seconds.
- Standard encoder comparison: 347.02 seconds.
- Observed reduction: approximately 34.2%.

These are measurements from a single system and workflow.

## 9. Known limitations

- Offloading 25 or more GPU layers caused Vulkan ErrorDeviceLost
  during repeated long-prompt tests on the RX 480.
- 12 and 24 layers passed the tested repeated-request sequence.
- System RAM usage remains high during Wan High/Low model switching.
- Other Polaris models, driver versions and operating systems
  require independent testing.
- Model files are not distributed in this repository.

## 10. Troubleshooting

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