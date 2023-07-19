"""
In this script we are going to collect data from Followin. We will navigate to this link:

https://followin.io/news

Once on it, we can extract all the latest news posts.

A simple GET request will return the page. We can then perform a lookup for all the elements following this structure:

<a href=/feed/[id]> :: returns the title and the link to the latest post
    --> go to a.parent.parent then access the first div element
    <div class="css-1rynq56"/>.text and select the 1st string using this regex: r'^(\d+)\s+(?:minute|minutes)\s+ago$'

With this, we can extract the links to every news post. They are ordered by post date, so once we reach a news post that
is outside of our time window, we can exit early.

Another GET request on the identified links (https://followin.io + /feed/[id] of interest will yield the relevant posts and their contents.

Once the GET request returns on the link of the post, look for these elements:

<h1 role="heading"/> :: the title of the news post
<a class="block max-w-max whitespace-nowrap text-ellipsis overflow-hidden mr-3"/> :: the author of the post
    --> get the parent of this element and look for this direct child:
    <div class="css-1rynq56"/> :: this will give us the date --> THIS DOES NOT SEEM TO WORK AS THE DATES DON'T MATCH REALITY ON THE WEBSITE
<div id="article-content"/> :: the content of the post

"""
import time
import re
import requests
import random
import asyncio
from bs4 import BeautifulSoup
from typing import AsyncGenerator
from datetime import datetime, timedelta
import pytz
from exorde_data import (
    Item,
    Content,
    Author,
    CreatedAt,
    Title,
    Url,
    Domain,
)
import logging

# GLOBAL VARIABLES
USER_AGENT_LIST = [
    'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
]
DEFAULT_OLDNESS_SECONDS = 360
DEFAULT_MAXIMUM_ITEMS = 25
DEFAULT_MIN_POST_LENGTH = 10


def request_content_with_timeout(_url, _time_delta):
    """
    Returns all relevant information from the news post
    :param _time_delta: the time in seconds since the post was put online
    :param _url: the url of the post
    :return: the content of the post

    <h1 role="heading"/> :: the title of the news post
    <a class="block max-w-max whitespace-nowrap text-ellipsis overflow-hidden mr-3"/> :: the author of the post
        --> get the parent of this element and look for this direct child:
        <div class="css-1rynq56"/> :: this will give us the date
    <div id="article-content"/> :: the content of the post
    """
    try:
        response = requests.get(_url, headers={'User-Agent': random.choice(USER_AGENT_LIST)}, timeout=8.0)
        soup = BeautifulSoup(response.text, 'html.parser')

        post_title = soup.find("h1", {"role": "heading"}).text
        content = soup.find("div", {"id": "article-content"}).text

        container = soup.find("a", {"class": "block max-w-max whitespace-nowrap text-ellipsis overflow-hidden mr-3"})
        author = container.text
        post_date = convert_date_to_standard_format(_time_delta)

        return Item(
            title=Title(post_title),
            content=Content(content),
            created_at=CreatedAt(post_date),
            url=Url(_url),
            domain=Domain("followin.io.com"))
    except Exception as e:
        logging.exception(f"[Followin] Error: {str(e)}")


async def request_entries_with_timeout(_url, _max_age):
    """
    Extracts all card elements from the latest news section
    :param _max_age: the maximum age we will allow for the post in seconds
    :param _url: the url where we will find the latest posts
    :return: the card elements from which we can extract the relevant information
    """
    try:
        response = requests.get(_url, headers={'User-Agent': random.choice(USER_AGENT_LIST)}, timeout=8.0)
        soup = BeautifulSoup(response.text, 'html.parser')
        all_a_tags = soup.find_all('a')
        entries = []
        for a in all_a_tags:
            if a.get("href") and "/feed/" in a.get("href"):
                entries.append(a)
        async for item in parse_entry_for_elements(entries, _max_age):
            yield item
    except Exception as e:
        logging.exception(f"[Followin] Error: {str(e)}")


def convert_date_to_standard_format(_time_delta):
    date = datetime.now(pytz.utc) - timedelta(seconds=_time_delta)
    return date.strftime("%Y-%m-%dT%H:%M:%S.00Z")


async def parse_entry_for_elements(_cards, _max_age):
    """
    Parses every card element to find the information we want
    :param _max_age: The maximum age we will allow for the post in seconds
    :param _cards: The parent card objects from which we will be gathering the information
    :return: All the parameters we need to return an Item instance
    """
    try:
        for card in _cards:
            date_element = card.parent.parent.findChild("div", {"class": "css-1rynq56"}, recursive=False).text.split()[:3]
            if date_element[1] == "minute" or date_element[1] == "minutes":
                time_delta = _max_age + 1
                if date_element[0] == "One":
                    time_delta = 60
                else:
                    time_delta = 60 * int(date_element[0])
                if time_delta <= _max_age:
                    item = request_content_with_timeout("https://followin.io" + card["href"], time_delta)
                    if item: yield item
                    else: break
                else:
                    break
            else:
                break
    except Exception as e:
        logging.exception(f"[Followin] Error: {str(e)}")


def read_parameters(parameters):
    # Check if parameters is not empty or None
    if parameters and isinstance(parameters, dict):
        try:
            max_oldness_seconds = parameters.get("max_oldness_seconds", DEFAULT_OLDNESS_SECONDS)
        except KeyError:
            max_oldness_seconds = DEFAULT_OLDNESS_SECONDS

        try:
            maximum_items_to_collect = parameters.get("maximum_items_to_collect", DEFAULT_MAXIMUM_ITEMS)
        except KeyError:
            maximum_items_to_collect = DEFAULT_MAXIMUM_ITEMS

        try:
            min_post_length = parameters.get("min_post_length", DEFAULT_MIN_POST_LENGTH)
        except KeyError:
            min_post_length = DEFAULT_MIN_POST_LENGTH

    else:
        # Assign default values if parameters is empty or None
        max_oldness_seconds = DEFAULT_OLDNESS_SECONDS
        maximum_items_to_collect = DEFAULT_MAXIMUM_ITEMS
        min_post_length = DEFAULT_MIN_POST_LENGTH

    return max_oldness_seconds, maximum_items_to_collect, min_post_length


async def query(parameters: dict) -> AsyncGenerator[Item, None]:
    url_main_endpoint = "https://followin.io/news"
    yielded_items = 0
    max_oldness_seconds, maximum_items_to_collect, min_post_length = read_parameters(parameters)
    logging.info(f"[Followin] - Scraping ideas posted less than {max_oldness_seconds} seconds ago.")

    async for item in request_entries_with_timeout(url_main_endpoint, max_oldness_seconds):
        yielded_items += 1
        yield item
        logging.info(f"[Followin] Found new post :\t {item.title}, posted at { item.created_at}, URL = {item.url}" )
        if yielded_items >= maximum_items_to_collect:
            break
