from setuptools import setup, find_packages

setup(
    name="fylix-cli",
    version="1.0.0",
    description="FYLIX - Secure file transfer with blockchain verification",
    author="FYLIX Team",
    packages=find_packages(),
    install_requires=[
        "typer>=0.9.0",
        "httpx>=0.25.0",
        "websockets>=12.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fylix=fylix.cli:app",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
)
