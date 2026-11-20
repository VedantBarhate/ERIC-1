# ERIC – Edge-Aware Raster-Guided Image Captioning

ERIC explores **semantic raster representations for remote sensing image captioning**, investigating whether spatially organized semantic information can serve as an alternative to conventional image-based representations.

The project is motivated by edge-oriented UAV applications, where image transmission and onboard processing can be challenging under bandwidth and computational constraints.

## Overview

ERIC uses a 7 × 7 spatial grid to divide remote sensing images into 49 cells. Each cell is assigned a semantic label using a scene-conditioned vocabulary, producing a structured semantic raster.

The project investigates three Transformer-based captioning configurations:

- **Image-only:** Caption generation using visual image features.
- **Raster-only:** Caption generation using semantic raster representations.
- **Image + Raster:** Caption generation using cell-level fusion of image and raster features.

## Architecture

```text
          RSICD Dataset
                |
                v
       Dataset Preparation
                |
                v
       7 × 7 Grid Division
                |
                v
    Scene-Conditioned Vocabulary
                |
                v
     Qwen-Based Semantic Labeling
                |
                v
        Semantic Raster Data
                |
                v
      RemoteCLIP Fine-Tuning
                |
                v
     Three Captioning Models
       /        |         \
   Image     Raster    Image +
    Only      Only     Raster
       \        |         /
                v
       Caption Evaluation
```

## Dataset

The project uses a working subset of the **Remote Sensing Image Captioning Dataset (RSICD)**.

| Property | Value |
|---|---:|
| Total images used | 2,806 |
| Scene categories | 8 |
| Grid resolution | 7 × 7 |
| Semantic cells per image | 49 |
| Train / Validation / Test | 2,244 / 281 / 281 |

Selected categories include airport, baseball field, beach, medium residential, pond, river, sparse residential, and stadium.

## Semantic Raster Generation

- Images are divided into 49 spatial cells.
- Scene-conditioned vocabularies constrain the available semantic labels.
- Qwen3.8-27B generates patch-level labels using numbered grid overlays.
- Generated labels are assembled into semantic raster representations.

*Note: Raster labels were automatically generated and were not manually verified.*

## RemoteCLIP Fine-Tuning

RemoteCLIP ViT-B/32 is fine-tuned using the generated patch-level semantic labels.

| Parameter | Configuration |
|---|---|
| Backbone | RemoteCLIP ViT-B/32 |
| Total parameters | 151.28M |
| Trainable parameters | 14.18M |
| Embedding dimension | 512 |
| Input resolution | 224 × 224 |
| Patch predictions | 49 |
| Optimizer | AdamW |
| Learning rate | 1e-5 |
| Epochs | 25 |
| Batch size | 32 |
| Training hardware | NVIDIA Tesla T4 |

**Test performance:**

- Patch-level accuracy: **55.43%**
- Macro-F1: 0.2437
- Balanced accuracy: 0.3315

## Captioning Experiments

| Configuration | Input | Decoder Layers |
|---|---|---:|
| 6a | Image-only | 3 |
| 6b | Raster-only | 8 |
| 6e | Image + Raster | 3 |

All configurations use the same random seed (42) and common test set. However, decoder depths and training settings differ.

## Evaluation Results

### Automatic Metrics

| Metric | Image-only | Raster-only | Image + raster |
|---|---:|---:|---:|
| BLEU-1 | 0.6423 | 0.5175 | 0.6006 |
| BLEU-2 | 0.4527 | 0.3719 | 0.4102 |
| BLEU-3 | 0.3381 | 0.2877 | 0.3041 |
| BLEU-4 | 0.2647 | 0.2357 | 0.2422 |
| METEOR | 0.4496 | 0.3487 | 0.4186 |
| ROUGE-L | 0.4715 | 0.4309 | 0.4186 |
| CIDEr | 0.6241 | 0.3354 | 0.2613 |

### Blind Human Evaluation

Captions are evaluated using four weighted criteria:

- Factual correctness – 35%
- Object and scene coverage – 25%
- Spatial and relational quality – 25%
- Language quality – 15%

| Configuration | Mean Score (/100) |
|---|---:|
| Image-only (6a) | 72.04 |
| Raster-only (6b) | **74.11** |
| Image + Raster (6e) | 61.38 |

The raster-only configuration achieves the highest mean human evaluation score, while the implemented fusion configuration does not outperform either individual modality.

## Repository Structure

| File | Description |
|---|---|
| `1_eric-classes-check.ipynb` | Dataset and class inspection |
| `2_rsicd-per-class-patch-vocabulary-generation.ipynb` | Patch vocabulary generation |
| `3a_patch_labeling_dataset_prep.ipynb` | Labeling dataset preparation |
| `3b_Qwen_Patch_Labeling.ipynb` | Qwen semantic labeling |
| `4_Raster_Review_Tool.py` | Raster review utility |
| `5_RemoteCLIP_FineTuning.ipynb` | RemoteCLIP fine-tuning |
| `6a_img_transformer_captioner.ipynb` | Image-only captioner |
| `6b_raster_transformer_captioner.ipynb` | Raster-only captioner |
| `6e_imgplusraster_transformer.ipynb` | Image-raster fusion captioner |
| `7_human_test_eval.py` | Blind human evaluation |

## Execution Workflow

Run the notebooks and scripts in the following order:

1. Dataset inspection and vocabulary generation.
2. Patch-labeling dataset preparation.
3. Qwen-based semantic raster generation.
4. RemoteCLIP fine-tuning.
5. Train the three captioning configurations.
6. Evaluate generated captions.

The project uses Python, PyTorch, Jupyter Notebook, RemoteCLIP, and vision-language models. GPU resources are recommended for model training and semantic labeling.

## Limitations and Future Work

- Semantic raster labels have not undergone manual verification.
- Patch-level classification performance requires improvement.
- Captioning configurations use different decoder depths and training settings.
- Physical edge-device deployment has not been performed.
- Bandwidth savings, inference latency, and energy consumption have not been measured.

Future work includes improving raster quality, investigating fusion strategies, conducting controlled experiments, and evaluating the framework on UAV-compatible edge hardware.

## Authors

**Vedant Nitin Barhate  · Achyut Tukaram Yesare · Vibhor Dev · Yash Pandey**
