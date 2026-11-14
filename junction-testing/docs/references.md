# Publications, datasets and repositories

What we built on, and what to read next. Links checked against our memory of the
literature; verify a link before citing it in the pitch.

## Methods we implemented ourselves in PyTorch

| Idea | Where we use it | Paper | Code to compare against |
| --- | --- | --- | --- |
| U-Net encoder-decoder with skips | PlanNet backbone (segmentation of walls, rooms, room edges, text) | Ronneberger, Fischer, Brox. *U-Net: Convolutional Networks for Biomedical Image Segmentation*. MICCAI 2015. arXiv:1505.04597 | many; we wrote our own (`backend/stoa/models.py`) |
| Objects as points (centre heatmaps) | PlanNet heat head: doors, windows, WCs, washbasins, bathtubs, showers, stoves. Count = number of peaks | Zhou, Wang, Krähenbühl. *Objects as Points* (CenterNet). 2019. arXiv:1904.07850 | github.com/xingyizhou/CenterNet |
| Penalty-reduced focal loss | heatmap loss `focal_heat_loss` | Law, Deng. *CornerNet*. ECCV 2018. arXiv:1808.01244; Lin et al. *Focal Loss*. ICCV 2017. arXiv:1708.02002 | |
| CRNN + CTC text recognition | GlyphNet reads room names, numbers, printed areas | Shi, Bai, Yao. *An End-to-End Trainable Neural Network for Image-based Sequence Recognition*. TPAMI 2017. arXiv:1507.05717; Graves et al. *Connectionist Temporal Classification*. ICML 2006 | github.com/bgshih/crnn |

## Floor plan recognition papers worth reading tomorrow

| Paper | Why it matters for us |
| --- | --- |
| Kalervo et al. *CubiCasa5K: A Dataset and an Improved Multi-Task Model for Floorplan Image Analysis*. SCIA 2019. arXiv:1904.01920. Code: github.com/CubiCasa/CubiCasa5k | Same Finnish plans as the Stoa `cubicasa5k` folder. Multi-task heatmaps + room/icon segmentation, very close to PlanNet. Their SVG parser (`floortrans/loaders/house.py`) is the reference for label semantics. |
| Liu, Wu, Kohli, Furukawa. *Raster-to-Vector: Revisiting Floorplan Transformation*. ICCV 2017. Code: github.com/art-programmer/FloorplanTransformation | Junction heatmaps + integer programming to get clean vector walls. Upgrade path for our wall polygons. |
| Zeng, Li, Yu, Fu. *Deep Floor Plan Recognition Using a Multi-Task Network with Room-Boundary-Guided Attention*. ICCV 2019. Code: github.com/zlzeng/DeepFloorplan | Room boundary vs room type heads: the same split as our `room` / `room_edge` channels. |
| Fan et al. *FloorPlanCAD: A Large-Scale CAD Drawing Dataset for Panoptic Symbol Spotting*. ICCV 2021. arXiv:2105.07147 | Symbol spotting on vector CAD drawings, relevant for the DXF/DWG files. |
| Chen, Liu, Wu, Furukawa. *Floor-SP: Inverse CAD for Floorplans by Sequential Room-wise Shortest Path*. ICCV 2019 | Room polygons with topology guarantees. |
| Dodge, Xu, Stenger. *Parsing floor plan images*. MVA 2017 | Early FCN wall segmentation plus OCR for room size; same "read printed area" idea. |

## Datasets

| Dataset | Licence | Use here |
| --- | --- | --- |
| Swiss Dwellings v3.0.0, Archilyse AG, doi:10.5281/zenodo.7788422 | CC BY 4.0 | Preview `swiss_dwellings` PNG/PDF/DXF triples. DXF gives pixel-perfect labels. |
| CubiCasa5K, zenodo.org/records/2613548 | CC BY-NC 4.0 | ~5000 annotated Finnish plans; trains the second PlanNet. Non-commercial only. |
| Stoa Junction preview (`questions.jsonl`) | per source, see `data/<source>/LICENSE.md` | Evaluation only. |

## Libraries

- ezdxf (DXF parsing): ezdxf.readthedocs.io
- PyMuPDF (PDF text layer and rendering): pymupdf.readthedocs.io
- OpenCV (contours, connected components, morphology): docs.opencv.org
- Google GenAI SDK (Gemini fallback): ai.google.dev/gemini-api/docs
