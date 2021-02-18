from setuptools import setup, find_packages

setup(
    name="one_ring",
    version="1.0.0",
    author="Yaser Amiri",
    author_email="yaser.amiri95@gmail.com",
    description="High level async programming",
    license="MIT",
    packages=find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    keywords="csp async asyncio nursery",
    zip_safe=False,
    include_package_data=True,
)
