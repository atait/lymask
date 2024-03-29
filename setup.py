from setuptools import setup
import os


def readme():
    with open('README.md', 'r') as fx:
      return fx.read()


setup(name='lymask',
      version='0.1.11',
      description='Mask dataprep with klayout',
      long_description=readme(),
      url='https://github.com/atait/lymask/',
      author='Alex Tait, Adam McCaughan, Sonia Buckley, Jeff Chiles, Jeff Shainline, Rich Mirin, Sae Woo Nam',
      author_email='alexander.tait@nist.gov',
      license='MIT',
      packages=['lymask'],
      install_requires=['klayout', 'lygadgets', 'PyYAML'],
      entry_points={'console_scripts': ['lymask=lymask.command_line:cm_main']},
      # package_data={'': ['*.lym']},
      include_package_data=True,
      cmdclass={},
      )
