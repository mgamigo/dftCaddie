import re, os
import setuptools


def get_version():
    with open(os.path.join("dftcaddie", "__init__.py"), "r") as f:
        content = f.read()
    return re.search(r'^__version__ = ["\']([^"\']*)["\']', content, re.M).group(1)


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dftcaddie",
    version=get_version(),
    author="Martin Gutierrez-Amigo",
    author_email="<martin.gutierrez.amigo@gmail.com>",
    description="A caddie for your DFT calculations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mgamigo/dftCaddie",
    packages=find_packages(exclude=("tests", "docs")),
    install_requires=[
        "pyyaml",
        "yaiv",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "caddie=dftcaddie.cli:main",
        ]
    },
    python_requires=">=3.10",
    include_package_data=True,
    package_data={
        "dftcaddie": ["data/**/*"],
    },
)
