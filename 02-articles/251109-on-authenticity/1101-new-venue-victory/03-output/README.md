# AI vs Human

Generated: 2025-11-11T19:11:30.076538Z  
Pipeline Version: 3.4

## CONTENTS

This bundle contains all outputs from a complete pipeline run analyzing
12 modules:

- nltk/ (9 files)
- transformers/ (7 files)
- nli/ (2 files)
- textstat_lex/ (8 files)
- spacy/ (9 files)
- semantic/ (10 files)
- ruptures/ (3 files)
- bertopic/ (13 files)
- final/ (4 files)
- calibration/ (3 files)
- lexicons/ (2 files)
- rapidfuzz/ (10 files)

## KEY FILES

outputs/final/
- content_complete_summary.json.   : Complete analysis schema
- report.html                      : Interactive HTML report
- timeline_heatmap.png             : Attribution timeline visualization
- hybrid_map.png                   : Change-point detection map

outputs/calibration/
- labels.parquet                   : Segment labels (human/synthetic/hybrid/uncertain)
- segments.parquet                 : Segment boundaries and features

outputs/ruptures/
- hybrid_seams.parquet             : Detected change-points
- feature_fusion.parquet           : Normalized feature matrix for detection

outputs/nltk/
- fw_burstiness_windows.parquet    : Window-level features (basis for all modules)

outputs/spacy/
- syntax_discourse_windows.parquet : Syntax & discourse features

outputs/lexicons/
- style_signals.parquet            : Hedge, idiom, intensifier densities

outputs/nli/
- nli_consistency.parquet          : Contradiction detection results

## QUICK START

1. View the HTML report: Open outputs/final/report.html in a browser
2. Access the schema: Load outputs/final/content_complete_summary.json
3. Analyze segments: Read outputs/calibration/labels.parquet with pandas

## MODULES

Module 0:  Foundations (paths, determinism, helpers)  
Module 1:  Lexical features (textstat, wordfreq)  
Module 2:  NLTK (stopwords, burstiness, windows)  
Module 3:  spaCy (syntax, discourse markers)  
Module 7:  Rapidfuzz (paraphrase entropy)  
Module 8:  Custom lexicons (hedges, idioms, intensifiers)  
Module 9:  NLI (contradiction detection)  
Module 10: Ruptures (change-point ensemble)  
Module 11: Calibration & labeling  
Module 12: Schema & final report