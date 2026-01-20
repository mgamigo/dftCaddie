import re, os
import setuptools


def get_version():
    with open(os.path.join("yaiv", "__init__.py"), "r") as f:
        content = f.read()
    return re.search(r'^__version__ = ["\']([^"\']*)["\']', content, re.M).group(1)


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dftcaddie",
    version=get_version(),
    author="Martin Gutierrez-Amigo",
    author_email="<martin.gutierrez.amigo@gmail.com>",
    description="TODO",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mgamigo/dftCaddie",
    packages=setuptools.find_packages(),
    install_requires=[
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
