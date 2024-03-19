from followinc645fc950d7f import query
import json
from exorde_data import Item
import pytest
import logging

@pytest.mark.asyncio
async def test_query():
    params = {
        "max_oldness_seconds": 1200,
        "maximum_items_to_collect": 5,
        # "min_post_length": 10,
        "keyword": "BTC"
    }
    async for item in query(params):
        logging.info(f"FOUND AN ITEM : {json.dumps(item, indent=4)}")
        assert isinstance(item, Item)

import asyncio
asyncio.run(test_query())
