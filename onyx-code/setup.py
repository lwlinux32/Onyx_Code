
from setuptools import setup, find_packages

setup(
    name='onyx-code',
    version='1.0.0',
    py_modules=['onyx_code'],
    install_requires=[
        'prompt_toolkit>=3.0.0',
        'litellm',
        'duckduckgo-search',
        'requests',
        'mcp',
        'anyio',
    ],
    entry_points={
        'console_scripts': [
            'onyx-code=onyx_code:main',
        ],
    },
    author='Onyx AI',
    description='A high-performance CLI-based AI coding assistant.',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)
