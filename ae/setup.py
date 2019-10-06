import os
import re
import setuptools


namespace_root = 'ae'

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


def replace_placeholders(file_content):
    return file_content \
        .replace('<{setup_path}>', setup_path) \
        .replace('<{package_name}>', package_name) \
        .replace('<{pip_name}>', pip_name) \
        .replace('<{import_name}>', import_name) \
        .replace('<{package_path}>', package_path) \
        .replace('<{package_version}>', package_version)


def read_package_version():             # also used by docs/conf.py (package need to be installed via pip install -e .)
    if os.path.exists(package_path + '.py'):
        file_name = package_path + '.py'
    elif os.path.exists(package_path + os.path.sep + '__init__.py'):
        file_name = package_path + os.path.sep + '__init__.py'
    else:
        raise RuntimeError(f"Main module of package {package_name} not found in {package_path}")
    with open(file_name) as fh:
        file_content = fh.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", file_content, re.M)
    if not version_match:
        raise RuntimeError(f"Unable to find version string of package {package_name} within {file_name}")
    return version_match.group(1)


def patch_read_me():
    with open("AE_PACKAGES_README.md") as fh:
        file_content = fh.read()
    file_content = replace_placeholders(file_content)
    with open("README.md", 'w') as fh:
        fh.write(file_content)
    return file_content


setup_path = os.path.abspath(os.path.dirname(__file__))
package_name = os.path.basename(setup_path)             # results in package name e.g. 'ae_core'
pip_name = package_name.replace(namespace_root + '_', namespace_root + '-')     # e.g. 'ae-core'
import_name = package_name.replace(namespace_root + '_', namespace_root + '.')  # e.g. 'ae.core'
package_path = os.path.abspath(package_name.replace(namespace_root + '_', namespace_root + os.path.sep))
package_version = read_package_version()


if __name__ == "__main__":
    long_description = patch_read_me()

    setuptools.setup(
        name=package_name,              # pip install name (not the import package name)
        version=package_version,
        author="Andi Ecker",
        author_email="aecker2@gmail.com",
        description=package_name + " sub-package/portion of python application environment namespace package",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://gitlab.com/ae-group/" + package_name,
        # don't needed for native/implicit namespace packages: namespace_packages=['ae'],
        # packages=setuptools.find_packages(),
        packages=setuptools.find_namespace_packages(include=[namespace_root]),  # find ae namespace module/sub-package
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
