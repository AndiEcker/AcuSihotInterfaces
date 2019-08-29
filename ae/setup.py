import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aepy",
    version="0.0.1",
    author="Andreas Ecker",
    author_email="aecker2@gmail.com",
    description="core modules of application environment for python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AndiEcker/aepy",
    # ae uses only core libs, so not needed to put: packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 1 - Planning",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
)

""" additional installations:
- pip install pytest
- pip install sphinx
- pip install sphinx-autodoc-typehints
- pip install sphinx-autodoc-annotation
- sudo apt-get install graphviz

"""
