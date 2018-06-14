from sphinx.setup_command import BuildDoc

cmdclass = {'build_sphinx': BuildDoc}

name = 'OBS matcher'
version = '0.1.0'
setup(
    name=name,
    author='Quentin Gliech',
    url='https://github.com/sandhose/obs-matcher',
    author_email='gliech@etu.unistra.fr',
    license='MIT',
    cmdclass=cmdclass,
    # these are optional and override conf.py settings
    command_options={
        'build_sphinx': {
            'project': ('setup.py', name),
            'version': ('setup.py', version)}},
)
