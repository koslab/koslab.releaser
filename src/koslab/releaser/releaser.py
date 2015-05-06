import subprocess, os, sys, re
from zest.releaser.vcs import BaseVersionControl
from zest.releaser import utils
import shutil
from ConfigParser import ConfigParser
from StringIO import StringIO
import argh
from datetime import datetime
import logging
logger = logging.getLogger('koslab.releaser')

class Releaser(object):

    def __init__(self, buildoutdir, sourcesdir, packages=None, 
                    releasercmd='fullrelease'):
        self.packages = packages or []
        self.buildoutdir = buildoutdir
        self.sourcesdir = sourcesdir
        self.releasercmd = releasercmd

    def release(self, prompt=True):
        directory = self.buildoutdir
        sourcesdir = self.sourcesdir
         
        versions = {}
        for package in self.packages:
            os.chdir('%s/%s/%s' % (directory, sourcesdir, package))
            p = subprocess.Popen(['git','log','-1'], stdout=subprocess.PIPE)
            retval = p.wait()
            out = p.stdout.read()
            if 'Back to development:' in out:
                logger.info("Skipping %s" % package)
                p = subprocess.Popen(['git','log','-2','--skip=1'], stdout=subprocess.PIPE)
                retval = p.wait()
                out = p.stdout.read()
                match = None
                for line in out.split('\n'):
                    match = re.match('.*Preparing release (.*?)$', line)
                    if match:
                        versions[package] = match.group(1)
                        break;
                continue
        
            if prompt:
                logger.info("Releasing %s" % package)
                os.system('git log | head -n 50')
                releaseme = raw_input('Release %s? (y/N/abort)' % package)
                if releaseme.lower().strip().startswith('a'):
                    sys.exit(1)
                elif releaseme.lower().strip() == 'y':
                    versions[package] = self._release(package)
            else:
                versions[package] = self._release(package)
        return versions


    def _release(self, package):
        version = utils.cleanup_version(
            BaseVersionControl()._extract_version()
        )
        os.system(self.releasercmd)
        return version
       
    def write_versionsfile(self, versions):
 
        versionfile = os.path.join(self.buildoutdir, 'releaseversions.cfg')
        oldversionfile = os.path.join(self.buildoutdir, 
                        'releaseversions.cfg.old')
        
        config = ConfigParser()
        if os.path.exists(versionfile):
            config.readfp(open(versionfile))
            shutil.move(versionfile, oldversionfile)
        
        if not config.has_section('versions'):
            config.add_section('versions')
        
        for key, version in versions.items():
            config.set('versions', key, version)
        
        stream = StringIO()
        config.write(stream)
        
        result = stream.getvalue()
        open(versionfile, 'w').write(result)
        logger.info(result)
        
    def run(self):
        versions = self.release()
        self.write_versionsfile(versions)

class DevelopmentReleaser(Releaser):

    def __init__(self, buildoutdir, sourcesdir, outputdir,
                    packages=None, releasercmd='python setup.py sdist'):
        super(DevelopmentReleaser, self).__init__(
            buildoutdir, sourcesdir, packages, releasercmd
        )
        self.outputdir = outputdir

    def _release(self, packagename):
        config = ConfigParser()
        origcfg = None

        if os.path.exists('setup.cfg'):
            origcfg = open('setup.cfg', 'r').read()
            config.readfp(open('setup.cfg'))

        if not config.has_section('egg_info'):
            config.add_section('egg_info')
        config.set('egg_info', 'tag_date', 'true')
        config.set('egg_info', 'tag_build', 'dev')

        if not config.has_section('sdist'):
            config.add_section('sdist')
        config.set('sdist', 'formats', 'zip')


        stream = StringIO()
        config.write(stream)
        open('setup.cfg', 'w').write(stream.getvalue())
        os.system(self.releasercmd)
        if origcfg is not None:
            open('setup.cfg', 'w').write(origcfg)
        else:
            os.remove('setup.cfg')
        version = utils.cleanup_version(
            BaseVersionControl()._extract_version()
        )

        date = datetime.now().strftime('%Y%m%d')
        version = '%sdev-%s' % (version, date)

        zipfile = '%s-%s.zip' % (packagename, version)
        outputdir = os.path.join(self.buildoutdir, self.outputdir)
        if not os.path.exists(outputdir):
            os.mkdir(outputdir)
        shutil.move(
            os.path.join(os.getcwd(), 'dist', zipfile), 
            os.path.join(outputdir, zipfile)
        )
        return version

    def run(self):
        versions = self.release(prompt=False)
        self.write_versionsfile(versions)

@argh.arg('buildoutdir')
@argh.arg('sourcesdir')
@argh.arg('packages', nargs='+')
def release(buildoutdir, sourcesdir, packages):
    Releaser(buildoutdir, sourcesdir, packages).run()

@argh.arg('buildoutdir')
@argh.arg('sourcesdir')
@argh.arg('outputdir')
@argh.arg('packages', nargs='+')
def devrelease(buildoutdir, sourcesdir, outputdir, packages):
    DevelopmentReleaser(buildoutdir, sourcesdir, outputdir, packages).run()

parser = argh.ArghParser()
parser.add_commands([release, devrelease])

def main():
    parser.dispatch()

if __name__ == '__main__':
    main()
