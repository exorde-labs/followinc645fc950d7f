from followinc645fc950d7f import query
from exorde_data import Item
import pytest
import logging

@pytest.mark.asyncio
async def test_query():
    params = {
        "max_oldness_seconds": 12000,
        "maximum_items_to_collect": 2,
        "min_post_length": 10
    }
    async for item in query(params):
        logging.info(item)
        assert isinstance(item, Item)

import asyncio
asyncio.run(test_query())
