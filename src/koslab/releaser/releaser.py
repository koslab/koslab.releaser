import subprocess, os, sys, re
from zest.releaser.vcs import BaseVersionControl
from zest.releaser import utils
import shutil
from ConfigParser import ConfigParser
from StringIO import StringIO
import argh
import logging
logger = logging.getLogger('koslab.releaser')

class Releaser(object):

    def __init__(self, buildoutdir, sourcesdir, packages=None, 
                    releasercmd='fullrelease'):
        self.packages = packages or []
        self.buildoutdir = buildoutdir
        self.sourcesdir = sourcesdir
        self.releasercmd = releasercmd

    def release(self):
        directory = self.buildoutdir
        sourcesdir = self.sourcesdir
         
        versions = {}
        for package in self.packages:
            os.chdir('%s/%s/%s' % (directory, sourcesdir, package))
            p = subprocess.Popen(['git','log','-1'], stdout=subprocess.PIPE)
            retval = p.wait()
            out = p.stdout.read()
            if 'Back to development:' in out:
                print "Skipping %s" % package
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
        
            print "Releasing %s" % package
            os.system('git log | head -n 50')
            releaseme = raw_input('Release %s? (y/N/abort)' % package)
            if releaseme.lower().strip() == 'y':
                versions[package] = utils.cleanup_version(
                    BaseVersionControl()._extract_version()
                )
                os.system(self.releasercmd)
            elif releaseme.lower().strip().startswith('a'):
                sys.exit(1)
        return versions
       
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
        print result
        
    def run(self):
        versions = self.release()
        self.write_versionsfile(versions)

@argh.arg('buildoutdir')
@argh.arg('sourcesdir')
@argh.arg('packages', nargs='+')
def release(buildoutdir, sourcesdir, packages):
    Releaser(buildoutdir, sourcesdir, packages).run()

parser = argh.ArghParser()
parser.add_commands([release])

def main():
    parser.dispatch()

if __name__ == '__main__':
    main()
