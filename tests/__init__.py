"""
tests/__init__.py
=================
Test suite root package for tech-news-agent.

Tests are organised by layer:
    - unit/      → fast, isolated tests with all AWS calls mocked.
    - integration/ → tests that call real AWS services (requires credentials).

TODO:
    - Add shared fixtures in conftest.py.
    - Add integration test suite once core tools are implemented.
"""
