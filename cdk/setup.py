from setuptools import setup, find_packages
from os import getenv

# Get the long description from the README file
# here = path.abspath(path.dirname(__file__))
# with open(path.join(here, "README.md"), encoding="utf-8") as f:
#     long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.


def get_micro():
    build_number: str = getenv("BUILD_NUMBER", "0")
    branch_name: str = getenv("BRANCH_NAME", "None")
    micro = build_number
    if branch_name != "master" and not branch_name.startswith("release"):
        micro = f"dev{build_number}+{''.join(e for e in branch_name if e.isalnum()).lower()}"
    return micro


setup(
    name="tenant-management-cdk",  # Required
    version=f"1.0.{get_micro()}",  # Required
    description="A sample Python project",  # Optional
    long_description="long_description",  # Optional
    long_description_content_type="text/markdown",  # Optional (see note above)
    author="Cyberark Ltd",  # Optional
    author_email="info@Cyberark.com",  # Optional
    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        # Pick your license as you wish
        "License :: OSI Approved :: MIT License",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        # These classifiers are *not* checked by 'pip install'. See instead
        # 'python_requires' below.
        "Programming Language :: Python :: 3.7",
    ],
    keywords="sample setuptools development",  # Optional
    packages=find_packages(exclude=["contrib", "docs", "tests"]),  # Required
    python_requires=">=3.7",
    install_requires=[
        "aws-cdk.core>=1.38.0",
        "aws_cdk.aws_cognito>=1.38.0",
        "aws-cdk.aws-dynamodb>=1.38.0",
        "aws-cdk.aws-iam>=1.38.0",
        "aws-cdk.aws-apigateway>=1.38.0",
        "aws-cdk.aws-events>=1.38.0",
        "aws-cdk.aws-lambda-event-sources>=1.38.0",
        "aws-cdk.aws-events-targets>=1.38.0",
        "aws-cdk.aws_ssm>=1.38.0",
        "aws-cdk.aws-stepfunctions>=1.38.0",
        "aws-cdk.aws-stepfunctions-tasks>=1.38.0",
    ],  # Optional
    extras_require={"dev": []},  # Optional
    project_urls={  # Optional
        "Bug Reports": "https://github.com/pypa/sampleproject/issues",
        "Funding": "https://donate.pypi.org",
        "Say Thanks!": "http://saythanks.io/to/example",
        "Source": "https://github.com/pypa/sampleproject/",
    },
)
