# ARWIF v0.1 Mini-Spec

ARWIF stands for Analog Resident Wave Information Format.

Version `0.1` is a narrow audio profile layered on top of the existing RWIF activation-core container. It is intended for compact storage of oscillator-bank instructions, not for PCM sample storage.

## Scope

ARWIF `v0.1` describes:

- a RWIF-compatible binary envelope
- integer-Hz oscillator definitions stored in RWIF atomic wave units
- sequential segment playback
- optional per-segment envelope and gain controls

It does not yet describe:

- multichannel layouts
- streaming or chunked playback
- compressed payloads
- sample-accurate event scheduling
- arbitrary wavetable synthesis

## Container

ARWIF reuses the RWIF activation-core envelope:

- magic header: `RWIFACT1`
- header prefix: little-endian `<8sI>`
- JSON header block
- packed atomic wave units using `<Id>`

That means generic RWIF tooling can still parse the file structure, even if it does not understand the audio semantics.

## Required Library Metadata

Strict ARWIF `v0.1` files should place these fields in `library_metadata`:

- `format = arwif_audio`
- `arwif_version = 1`
- `frequency_unit = hz`
- `playback_model = continuous_oscillator_bank`
- `sample_rate_hz = <positive integer>`
- `default_duration_seconds = <positive float>`

Optional library metadata:

- `title`
- `normalize` as boolean, default `true`
- `default_phase_radians`, default `0.0`
- `default_attack_ms`, default `5.0`
- `default_release_ms`, default `5.0`

## State Semantics

Each RWIF state is interpreted as one sequential audio segment.

States are rendered in file order.
All atomic wave units inside a state are rendered simultaneously as a summed oscillator bank.

State metadata may override library defaults with:

- `duration_seconds`
- `phase_radians`
- `gain`
- `attack_ms`
- `release_ms`

## Atomic Wave Unit Semantics

ARWIF `v0.1` reinterprets the RWIF unit fields as:

- `frequency_index` slot: integer frequency in Hz
- `amplitude` slot: linear amplitude scalar

This is a semantic reinterpretation of the RWIF unit struct. In semantic-memory RWIF, the integer slot is a transformed coefficient index. In ARWIF, it is oscillator frequency.

## Compatibility Field Note

The RWIF `vector_length` field is retained for envelope compatibility with existing loaders, but ARWIF decoders should not treat it as a hard frequency bound.

For ARWIF `v0.1`, frequency validation is based on `sample_rate_hz` and Nyquist, not on `vector_length`.

## Rendering Model

The reference renderer produces mono 16-bit PCM WAV output.

For each segment:

1. create a time grid using `sample_rate_hz`
2. synthesize one sine oscillator per atomic wave unit
3. sum the oscillators
4. apply gain and a simple attack/release envelope
5. concatenate segments in order
6. normalize if enabled

## Authoring Spec

The reference builder command accepts a YAML or JSON spec and writes a strict ARWIF `v0.1` artifact.

Minimum shape:

```yaml
title: C major triad
sample_rate_hz: 48000
default_duration_seconds: 1.0

states:
  - label: CEG
    duration_seconds: 1.0
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 330
        amplitude: 0.7
      - hz: 392
        amplitude: 0.6
```

Supported top-level fields:

- `title`
- `description`
- `sample_rate_hz`
- `default_duration_seconds`
- `default_phase_radians`
- `default_attack_ms`
- `default_release_ms`
- `normalize`
- `metadata` for additional library metadata
- `states`

Supported per-state fields:

- `label`
- `duration_seconds`
- `phase_radians`
- `gain`
- `attack_ms`
- `release_ms`
- `vector_length`
- `top_k`
- `metadata` for additional state metadata
- `oscillators`, where each oscillator is `{ hz, amplitude }`

Reference command:

```bash
rwif arwif-build --spec examples/arwif/CEG_v0_1.yaml --output dist/CEG_v0_1.arwif --json
```

## Legacy Prototype Files

Pre-spec ARWIF prototype files may omit the strict metadata fields while still reusing the `RWIFACT1` envelope and oscillator-bank interpretation.

Reference tooling may support these files in a legacy-compatibility mode, but they should not be considered fully compliant ARWIF `v0.1` artifacts.