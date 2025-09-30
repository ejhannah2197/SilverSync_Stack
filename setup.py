from setuptools import setup, find_packages

setup(
    name="silversync",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "blinker==1.9.0",
        "click==8.3.0",
        "colorama==0.4.6",
        "DateTime==5.5",
        "Flask==3.1.2",
        "GeoAlchemy2==0.18.0",
        "greenlet==3.2.4",
        "itsdangerous==2.2.0",
        "Jinja2==3.1.6",
        "MarkupSafe==3.0.2",
        "names==0.3.0",
        "numpy==2.3.3",
        "packaging==25.0",
        "psycopg2==2.9.10",
        "pytz==2025.2",
        "setuptools==80.9.0",
        "shapely==2.1.2",
        "SQLAlchemy==2.0.43",
        "typing_extensions==4.15.0",
        "Werkzeug==3.1.3",
        "zope.interface==8.0.1",
    ],
    python_requires=">=3.11",
    description="SilverSync full-stack monitoring system",
    author="Elijah Hannah",

)