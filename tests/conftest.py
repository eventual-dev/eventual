import asyncio

import pytest
from tortoise.contrib.test import finalizer, initializer


# @pytest.yield_fixture(scope="session")
# def event_loop(request):
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()
#
#
@pytest.fixture(scope="session", autouse=True)
def initialize_tests(request):
    initializer(
        ["gum.infra.relation"],
        db_url="sqlite://:memory:",
        app_label="models",
    )
    request.addfinalizer(finalizer)
