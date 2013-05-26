from setuptools import setup, find_packages
import os
version = "0.0"
install_requires = ["pyramid",
                    "jinja2",
                    "beautifulsoup4",
                    "markdown",
                    "typogrify",
                    "pygments"]

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md")) as f:
    README = f.read()
with open(os.path.join(here, "CHANGES.md")) as f:
    CHANGES = f.read()
with open(os.path.join(here, "LICENSE.txt")) as f:
    LICENSE = f.read()

DESCRIPTION = README + "\n\n" + CHANGES


setup(name="diredly",
      version=version,
      description="micro static site generator",
      long_description=DESCRIPTION,
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Console",
                   "License :: OSI Approved :: Simplified BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 2.7",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Software Development :: Libraries :: Python Modules",],
      keywords="",
      author="Thomas G. Willis",
      author_email="tom@batterii.com",
      url="",
      license=LICENSE,
      packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      diredly_export=diredly.scripts.diredly_export:main
      """,
      )
