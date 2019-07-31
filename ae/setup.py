import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="app-env",
    version="0.0.1",
    author="Andreas Ecker",
    author_email="aecker2@gmail.com",
    description="python application environment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AndiEcker/aepy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)
