def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "known_gap: the API behaves differently from what a production API should (documented, not a test bug)",
    )
