# CEG.arwif - Documentation Sidecar

## 1. Intended Meaning of ARWIF
**ARWIF** stands for **A**nalog **R**esident **W**ave **I**nformation **F**ormat.

## 2. RWIF Compatibility
ARWIF is fully RWIF-compatible at the structure level. It uses the same `RWIFACT1` magic header and the same binary unit struct. It is optimized for real-time wave synthesis.

## 3. Harmonic Data
The chord stored in `CEG.arwif` represents a root-position C Major Triad (C4, E4, G4).
*   **C (261 Hz):** Frequency Index 261, Amplitude 0.8
*   **E (330 Hz):** Frequency Index 330, Amplitude 0.8
*   **G (392 Hz):** Frequency Index 392, Amplitude 0.8

## 4. Format Assumptions
*   **Magic Header:** `RWIFACT1` (8 bytes).
*   **Envelope/Phase/Duration:** Currently, the format captures the static wave-state. Playback semantics (duration/envelope) are not yet natively encoded, implying a continuous-state wave generator.
