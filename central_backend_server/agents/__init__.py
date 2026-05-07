"""
The three agents from the paper, plus glue.

  - generator: builds an EBM-grounded vignette and picks an avatar
  - vsp:       virtual simulated patient — generates persona-consistent dialogue
  - critic:    quick + final feedback and on-demand hints
  - predefined: skips generation, loads a hard-coded patient
  - lifecycle: stop_patient and on-disk patient artifacts
"""
