from setuptools import setup, find_packages

setup(
    name="task-prioritizer",
    version="0.1.2",
    description="A calm CLI tool for choosing what to work on and knowing when to stop",
    author="Rene Lachmann",
    packages=find_packages(),
    install_requires=[
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "task-prioritizer=task_prioritizer.main:main",
            "tp=task_prioritizer.main:main",
        ],
    },
    python_requires=">=3.8",
)
