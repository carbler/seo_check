from setuptools import setup, find_packages

setup(
    name="seo_check",
    version="0.1.2",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "advertools>=0.15.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "rich>=13.0.0",
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.20.0",
        "python-multipart>=0.0.5",
        "jinja2>=3.1.0",
        "requests>=2.28.0",
        "websockets>=10.0",
        "httpx",
        "lxml",
        "scrapy", # Often needed by advertools implicitly or explicitly for crawling
    ],
    entry_points={
        "console_scripts": [
            "seo-check=seo_check.main:cli",
        ],
    },
    author="Your Name",
    description="A CLI tool for SEO analysis with web reporting capabilities.",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
