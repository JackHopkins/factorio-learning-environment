"""Setup information"""

import setuptools

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

setuptools.setup(
    name="factorio-rcon-py",
    version="1.2.1",
    author="mark9064",
    description="A simple factorio RCON client",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/mark9064/factorio-rcon-py",
    packages=setuptools.find_packages(),
    install_requires=["construct"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
    ],
)
