# this is the setup file - run once only to make the package:
# python setup.py sdist
# will make the tarball. This can be unpacked then:
# python setup.py install --prefix=/usr/local/bin

from distutils.core import setup, Extension

setup(name='RTIAcquire',
    version='1.2dev',
    packages=['rtiacquire'],
    scripts=['bin/RTIAcquire'],
    author='J. Cupitt',
    author_email='jcupitt@gmail.com',
    license='LICENSE.txt',
    description='Remote-control of digital cameras', 
    ext_modules=[Extension('rtiacquire.dejpeg', ['rtiacquire/dejpeg.c'], 
        libraries=['jpeg'], extra_compile_args=['-Wno-error=unused-command-line-argument-hard-error-in-future'])],
    package_data={'rtiacquire': ['data/*']},
    requires=['pyserial'],
    long_description=open('README.md').read(),
)
