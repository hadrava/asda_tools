import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="asda_tools",
    version="0.0.1",
    author="Jan Hadrava",
    author_email="had@kam.mff.cuni.cz",
    description="Parser for .par files produced by ASDASoft",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hadrava/asda_tools",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.4',
)
