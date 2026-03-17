# MVP Contract

## Goal

The `rwif-builder` MVP should make it straightforward to turn local content into a deterministic, validated `.rwif` artifact that can be shipped into RWIF-backed retrieval systems.

## In Scope

- local filesystem ingestion
- Markdown and text inputs first
- deterministic normalization and chunking
- manifest generation with source hashes and build metadata
- structural validation
- summary inspection
- artifact diffing
- patch planning for incremental rebuilds

## Out Of Scope

- GUI applications
- remote crawlers
- collaborative editing
- hosted indexing APIs
- benchmark claim generation
- heavy runtime serving concerns

## Success Standard

A user should be able to do the following without custom code:

1. create a config
2. build an RWIF artifact from a docs folder
3. validate the result
4. inspect what was written
5. compare one artifact against another
