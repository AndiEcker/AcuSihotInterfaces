import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="app-env-py-core",
    version="0.0.1",
    author="Andreas Ecker",
    author_email="aecker2@gmail.com",
    description="core modules of application environment for python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AndiEcker/aepy_core",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)

""" additional installations:
- pip install pytest
- pip install sphinx
- pip install sphinx-autodoc-typehints
- pip install sphinx-autodoc-annotation
- sudo apt-get install graphviz

"""