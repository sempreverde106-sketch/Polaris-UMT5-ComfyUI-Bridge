# Polaris UMT5 ComfyUI Bridge

**Give legacy AMD GPUs a second life in modern AI workflows.**

An experimental project that runs the UMT5-XXL GGUF text encoder on a legacy AMD Polaris GPU through Vulkan, using a modified llama.cpp server and a custom ComfyUI conditioning bridge.

The goal is to offload text encoding from the primary GPU, reducing VRAM pressure and improving performance in Wan 2.2 video generation.

## Tested Hardware

- Primary GPU: AMD Radeon RX 6950 XT 16GB
- Secondary GPU: AMD Radeon RX 480 8GB (Polaris)
- CPU: AMD Ryzen 7 5700X3D
- System RAM: 32GB DDR4
- OS: Windows 11
- Text encoder: UMT5-XXL Q5_K_M GGUF
- Backend: Vulkan (llama.cpp)
- Workflow: ComfyUI + Wan 2.2 High/Low Noise

## Benchmark Results

Two consecutive video generations, using the same test workflow:

| Configuration | First video | Second video | Total |
|---|---:|---:|---:|
| Standard ComfyUI text encoder | 205.83s | 141.19s | 347.02s |
| RX 480 dedicated text encoder | 118.36s | 110.05s | 228.41s |

**34.2% reduction in total execution time** in this test.

Additional observations:

- Approximately 2.3GB lower peak VRAM on the primary GPU in each run.
- 10/10 consecutive encoder requests completed successfully with 12 GPU layers.
- Mean cosine similarity against the CPU reference: 0.999514 (13-token comparison).
- Two consecutive Wan 2.2 videos generated successfully using the RX 480 bridge.

Results are specific to the tested system and workflow. Wider compatibility and performance are not yet established.

## Architecture

1. The RX 480 runs a persistent Vulkan llama.cpp text-encoder service.
2. A custom ComfyUI node sends prompts to the service.
3. The service returns UMT5 token embeddings.
4. The bridge formats the embeddings as Wan-compatible conditioning.
5. The RX 6950 XT performs video generation.

## Known Limitations

- Tested successfully on RX 480 8GB only.
- The custom llama.cpp encoder modifications are required.
- Offloading 25 or more GPU layers triggered Vulkan `ErrorDeviceLost` during repeated long-prompt testing.
- The 12-layer configuration passed repeated-request and video-generation tests, but long-term stability remains under evaluation.
- Peak system RAM usage remains high during Wan model switching.

## Project Status

**Experimental — work in progress.**

Source patches, ComfyUI nodes, installation instructions and reproducible tests will be added after verification.

This project is not affiliated with AMD, ComfyUI, llama.cpp or the Wan model developers.
