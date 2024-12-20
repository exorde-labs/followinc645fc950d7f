from setuptools import find_packages, setup

setup(
    name="followinc645fc950d7f",
    version="0.0.36",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pytz",
        "exorde_data",
        "aiohttp",
        "beautifulsoup4>=4.11"
    ],
    extras_require={"dev": ["pytest", "pytest-cov", "pytest-asyncio"]},
)
