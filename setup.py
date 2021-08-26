from setuptools import setup

setup(
   name='display_csv',
   version='0.1',
   description='Display CSV files',
   author='Alexander Senf',
   author_email='ajsenf@gmail.com',
   packages=['display_csv'],
   install_requires=['click', 'matplotlib', 'pandas', 'psutils', 'seaborn', 'watchdog'],
)