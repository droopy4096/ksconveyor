#!/usr/in/python

"""Assemble Kickstart from reusable pieces
FS structure:

BASE_DIR/
  parts
    commands/
      comm1
      comm2
    packages/
      pkg1
      pkg2
    pre/
      pre1
      pre2
    post/
      post1
      post2
    post.header/
      header1
  templates/
    templateA/
      commands/
        comm1 -> ../../parts/commands/comm1
      packages/
        pkg2 -> ../../parts/packages/pkg2
      pre/
        pre1 -> ../../parts/pre/pre1
      post/
        post1 -> ../../parts/post/post1
      post.header/
        header1 -> ../../parts/post.header/header1
     templateB/
      ...

"""

from __future__ import print_function
import sys
import argparse
import os
import os.path

## BASE_DIR='/srv/ks/conveyor'

DECOR_DIR=1
DECOR_FILE=2

SECTIONS=('commands','packages','pre','post','post.header')

class Cat(object):
    _pre=None
    _post=None
    # _decorate_per_dir=None
    _decor_mode=None
    _ignore_dirs=None
    _header_call=None

    def __init__(self):
        # self._decorate_per_dir=False
        self._decor_mode=2
        self._ignore_dirs=[]
        self.resetDecor()
        self._header_call=None

    def setPreamble(self,pre):
        self._pre=pre

    def setPS(self,ps):
        self._post=ps

    def setDecor(self,decor):
        self._decor_mode=decor

    def resetDecor(self):
        self._pre=''
        self._post=''
        self._header_call=None

    def setIgnoreDirs(self,ignore_dirs):
        self._ignore_dirs=ignore_dirs

    def setHeaderCall(self,hc):
        """function that would take 1 argument - DECOR_MODE"""
        self._header_call=hc

    def echo(self,my_text):
        print(my_text)

    def __call__(self,path):
        preamble=self._pre
        ps=self._post
        # dpd=self._decorate_per_dir
        dpf=self._decor_mode & DECOR_FILE
        dpd=self._decor_mode & DECOR_DIR
        ignore_dirs=self._ignore_dirs

        if os.path.isfile(path):
            dir_basename=os.path.basename(os.path.dirname(path))
            file_basename=os.path.basename(path)
            if preamble:
                self.echo(preamble.format(path=path,dir_basename=dir_basename,file_basename=file_basename))
            if self._header_call:
                self._header_call(DECOR_FILE)
            f=open(path,'r')
            self.echo(f.read())
            f.close()
            if ps:
                self.echo(ps.format(path=path,dir_basename=dir_basename,file_basename=file_basename))
        elif os.path.isdir(path):
            dir_basename=os.path.basename(path)
            if not (dir_basename in ignore_dirs):
                if dpd:
                    self.echo(preamble.format(path=path,dir_basename=dir_basename,file_basename=''))
                    if self._header_call:
                        self._header_call(DECOR_DIR)
                listdir=os.listdir(path)
                listdir.sort()
                for filename in listdir:
                    file_path=os.path.join(path,filename)
                    if preamble and dpf:
                        self.echo(preamble.format(path=file_path,dir_basename=dir_basename,file_basename=filename))
                    if dpf and self._header_call:
                        self._header_call(DECOR_FILE)
                    f=open(file_path,'r')
                    self.echo(f.read())
                    f.close()
                    if ps and dpf:
                        self.echo(ps.format(path=file_path,dir_basename=dir_basename,file_basename=filename))
                if dpd:
                    self.echo(ps.format(path=path,dir_basename=dir_basename,file_basename=''))
        
class Assembler(object):
    _base_dir=None
    _ignore_dirs=None
    def __init__(self,base_dir,ignore_dirs):
        self._base_dir=base_dir
        self._ignore_dirs=ignore_dirs

    def setup(self,template_id):
        template_dir=os.path.join(self._base_dir,'templates',template_id)
        ks_commands=os.path.join(template_dir,'commands')
        ks_packages=os.path.join(template_dir,'packages')
        ks_pre=os.path.join(template_dir,'pre')
        ks_post=os.path.join(template_dir,'post')
        ks_post_header=os.path.join(template_dir,'post.header')
        def _my_mkdir(my_dir):
            try:
                os.makedirs(my_dir)
            except OSError:
                # very crude, should handle errorcode instead:
                # OSError: [Errno 17] File exists: '
                pass
        _my_mkdir(ks_commands)
        _my_mkdir(ks_packages)
        _my_mkdir(ks_pre)
        _my_mkdir(ks_post)
        _my_mkdir(ks_post_header)

    def listparts(self):
        template_dir=os.path.join(self._base_dir,'parts')
        ks_commands=os.path.join(template_dir,'commands')
        ks_packages=os.path.join(template_dir,'packages')
        ks_pre=os.path.join(template_dir,'pre')
        ks_post=os.path.join(template_dir,'post')
        ks_post_header=os.path.join(template_dir,'post.header')
        
        cat=Cat()
        # cat.echo('commands')
        for cmd in os.listdir(ks_commands):
            if not (cmd in self._ignore_dirs):
                cat.echo('commands '+cmd)

        for pkg in os.listdir(ks_packages):
            if not (pkg in self._ignore_dirs):
                cat.echo('packages '+pkg)

        for pre in os.listdir(ks_pre):
            if not (pre in self._ignore_dirs):
                cat.echo('pre '+pre)

        for post_header in os.listdir(ks_post_header):
            if not (post_header in self._ignore_dirs):
                cat.echo('post.header '+post_header)

        for post in os.listdir(ks_post):
            if not (post in self._ignore_dirs):
                cat.echo('post '+post)

    def create(self,template_id,parts):
        parts_dir=os.path.join(self._base_dir,'parts')
        
        template_dir=os.path.join(self._base_dir,'templates',template_id)

        cat=Cat()
        # create FS layout
        self.setup(template_id)

        # for p in parts.keys():
        for p in SECTIONS:
            # walking through sections: commands,packages,pre,post,post.header
            if not parts.has_key(p):
                continue
            for pe in parts[p]:
                # we have just hardcoded FS layout...
                src_part=os.path.join('../../../parts',p,pe)
                dst_part=os.path.join(template_dir,p,pe)
                try:
                    os.symlink(src_part,dst_part)
                except OSError:
                    print("Can't link {1} to {0}, skipping".format(src_part,dst_part))

    def clone(self,src_template_id,dst_template_id):
        pass

    def assemble(self,template_id,pkg_opts,ignore_dirs):
        template_dir=os.path.join(self._base_dir,'templates',template_id)
        ks_commands=os.path.join(template_dir,'commands')
        ks_packages=os.path.join(template_dir,'packages')
        ks_pre=os.path.join(template_dir,'pre')
        ks_post=os.path.join(template_dir,'post')
        ks_post_header=os.path.join(template_dir,'post.header')

        cat=Cat()
        sub_cat=Cat()
        cat.setIgnoreDirs(ignore_dirs)

        cat.echo("## Auto-generated by conveyor line")
        cat(ks_commands)

        cat.echo("\n%packages "+pkg_opts)
        cat(ks_packages)
        cat.echo("%end\n")

        cat.setPreamble("\n%pre")
        cat.setPS("%end\n")
        cat(ks_pre)

        cat.setDecor(DECOR_FILE)
        def post_header(x):
            if x & DECOR_FILE:
                sub_cat(ks_post_header)
        cat.setHeaderCall(post_header)
        cat.setPreamble("\n%post --erroronfail --log=/root/anaconda-{file_basename}.log")
        cat(ks_post)
        cat.resetDecor()

if __name__ == '__main__':
    parser=argparse.ArgumentParser()

    parser.add_argument('--base-dir','-b',type=str,help='',default='.')
    parser.add_argument('--ignore-dirs','-i',type=str,help='',default='RCS')
    subparsers=parser.add_subparsers(dest='command',help='')

    parser_assemble=subparsers.add_parser('assemble')
    parser_assemble.add_argument('--template-id','-t',type=str,help='',required=True,default=None)
    parser_assemble.add_argument('--packages-opts','-o',type=str,help='',default='--nobase')

    parser_assemble=subparsers.add_parser('init')
    parser_assemble.add_argument('--template-id','-t',type=str,help='',required=True,default=None)

    parser_assemble=subparsers.add_parser('listparts')

    parser_assemble=subparsers.add_parser('listtemplates')

    parser_assemble=subparsers.add_parser('clone')

    parser_assemble=subparsers.add_parser('create')
    parser_assemble.add_argument('--template-id','-t',type=str,help='',required=True,default=None)
    for s in SECTIONS:
        parser_assemble.add_argument('--'+s,type=str,help='',required=True,default=None)

    args=parser.parse_args(sys.argv[1:])
    ignore_dirs=args.ignore_dirs.split(',')
    if args.command == 'assemble':
        a=Assembler(args.base_dir,ignore_dirs)
        a.assemble(args.template_id,args.packages_opts,ignore_dirs)
    elif args.command=='init':
        a=Assembler(args.base_dir,ignore_dirs)
        a.setup(args.template_id)
    elif args.command=='listparts':
        a=Assembler(args.base_dir,ignore_dirs)
        a.listparts()
    elif args.command=='create':
        a=Assembler(args.base_dir,ignore_dirs)
        my_parts={}
        vargs=vars(args)
        for s in SECTIONS:
            my_parts[s]=vargs[s].split(',')
        a.create(args.template_id,my_parts)

