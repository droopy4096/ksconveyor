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

BASE_DIR='/srv/ks/conveyor'

##TEMPLATE_NAME=${1}

##KS_COMMANDS=${BASE_DIR}/templates/${TEMPLATE_NAME}/commands
##KS_PACKAGES=${BASE_DIR}/templates/${TEMPLATE_NAME}/packages
##KS_PRE=${BASE_DIR}/templates/${TEMPLATE_NAME}/pre
##KS_POST=${BASE_DIR}/templates/${TEMPLATE_NAME}/post
##KS_POST_HEADER=${BASE_DIR}/templates/${TEMPLATE_NAME}/post.header
##PACKAGES_OPTS=${PACKAGES_OPTS:-"--nobase"}
##IGNORE_DIRS="RCS"

class Assembler(object):
    _base_dir=None
    def __init__(self,base_dir):
        self._base_dir=base_dir

    def assemble(self,template_id,pkg_opts,ignore_dirs):
        template_dir=os.path.join(self._base_dir,'templates',template_id)
        ks_commands=os.path.join(template_dir,'commands')
        ks_packages=os.path.join(template_dir,'packages')
        ks_pre=os.path.join(template_dir,'pre')
        ks_post=os.path.join(template_dir,'post')
        ks_post_header=os.path.join(template_dir,'post.header')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()

    parser.add_argument('--base-dir','-b',type=str,help='',default='.')
    subparsers=parser.add_subparsers(dest='command',help='')

    parser_assemble=subparsers.add_parser('assemble')
    parser_assemble.add_argument('--template-id','-t',type=str,help='',required=True,default=None)
    parser_assemble.add_argument('--packages-opts','-o',type=str,help='',default='--nobase')
    parser_assemble.add_argument('--ignore-dirs','-i',type=str,help='',default='RCS')

    args=parser.parse_args(sys.argv[1:])
    if args.command == 'assemble':
        a=Assembler(args.base_dir)
        a.assemble(args.template_id,args.packages_opts,args.ignore_dirs)

