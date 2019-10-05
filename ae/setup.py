import setuptools


__version__ = "0.0.1"


with open("README.md") as fh:
    long_description = fh.read()

docs_require = [
    'sphinx',
    'sphinx-autodoc-typehints',
    'sphinx_rtd_theme',     # since Sphinx 1.4 no longer integrated (like alabaster)
    'sphinx_paramlinks',
    # typehints extension does that already so no need to also include 'sphinx-autodoc-annotation',
]

tests_require = [
    'pytest',
    'pytest-cov',
]

if __name__ == "__main__":
    setuptools.setup(
        name="ae",              # pip install name (not the import package name)
        version=__version__,
        author="Andi Ecker",
        author_email="aecker2@gmail.com",
        description="core modules of python application environment namespace package",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://gitlab.com/ae-group/ae",
        namespace_packages=['ae'],
        # packages=setuptools.find_packages(),
        packages=setuptools.find_namespace_packages(include=['ae.*']),  # find all namespace packages
        python_requires=">=3.6",
        extras_require={
            'docs': docs_require,
            'tests': tests_require,
            'dev': docs_require + tests_require,
        },
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
        keywords=[
            'productivity',
            'application',
            'environment',
            'configuration',
            'development',
        ]
    )
