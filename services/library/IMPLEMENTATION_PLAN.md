# Implementation Plan: Recursive Dependency Resolution & Conflict Detection

## Goal
Enhance `find_library_dependencies` to support recursive dependency fetching (up to a specified depth), detect version conflicts across the dependency tree, and suggest resolved versions.

## Architecture
1.  **Model Updates**:
    *   Add `depth` (int, default=1) to `LibraryQuery`.
    *   Update `TaskResult` to include `conflicts` (list) and `suggested_versions` (dict).
    *   Enhance `DependencyInfo` to support nested dependencies or a flat tree structure with parent references.
2.  **Recursive Logic**:
    *   Implement a Breadth-First Search (BFS) in `BatchProcessor` (or a new `DependencyResolver` class) to fetch dependencies layer by layer.
    *   Use existing `Worker.get_dependencies` for fetching, but orchestrate it centrally to manage caching and deduplication.
3.  **Conflict Detection**:
    *   Track all version constraints for each library encountered.
    *   Use `packaging.specifiers` (Python) and basic semver matching (others) to check if constraints are disjoint.
    *   Report conflicts: `{library: [constraint1 (from A), constraint2 (from B)]}` where intersection is empty.
4.  **Version Suggestion**:
    *   If no conflict, suggest the highest version satisfying all constraints.
    *   If conflict, suggest resolving to the version required by the direct dependency or the majority.

## Stage 1: Models & Core Logic
**Goal**: Define data structures and implement version parsing/matching logic.
**Files**: `src/library/models.py`, `src/library/core/version_utils.py` (new)
**Tests**: Unit tests for version intersection and conflict detection.

## Stage 2: Recursive Resolver
**Goal**: Implement the recursive fetching loop.
**Files**: `src/library/core/processor.py`, `src/library/core/resolver.py` (new)
**Tests**: Mocked worker tests ensuring BFS works and depth limit is respected.

## Stage 3: Integration & Worker Updates
**Goal**: Ensure all language workers return parseable constraints and integrate with the resolver.
**Files**: `src/library/workers/*.py` (minor updates if needed for standardization)
**Tests**: Integration test with `requests` (Python) or `express` (Node) to see real recursion.

## Stage 4: API & Documentation
**Goal**: Expose new parameters and fields.
**Files**: `src/library/core/server.py`, `API_REFERENCE.md`
**Tests**: End-to-end MCP tool test.
