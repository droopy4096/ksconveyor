#!/usr/bin/python

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
import re
import ConfigParser

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
    _translate=None
    _vars=None
    _lookup_mode=None

    def __init__(self):
        # self._decorate_per_dir=False
        self._decor_mode=2
        self._ignore_dirs=[]
        self.resetDecor()
        self._header_call=None
        self._translate=False
        self._translate_extractor=re.compile(r'@@(\w+)@@')
        self._vars=set()
        self._lookup_mode=False

    def setTranslate(self,trans):
        self._translate=trans

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

    def _var_lookup(self,var):
        if os.environ.has_key(var):
            return os.environ[var]
        else:
            return None

    def setLookupMode(self,lm):
        self._lookup_mode=lm

    def seenVars(self):
        return self._vars

    def listVars(self,my_text):
        return self._translate_extractor.findall(my_text)

    def _translator(self,my_text):
        sub_vars=self.listVars(my_text)
        for sv in sub_vars:
            self._vars.add(sv)
        # print(sub_vars)
        res_text=my_text
        for my_var in sub_vars:
            my_sub=self._var_lookup(my_var)
            if not my_sub is None:
                res_text=re.sub('@@'+my_var+'@@',my_sub,res_text)
        return res_text

    def echo(self,my_text):
        if self._translate:
            print_text=self._translator(my_text)
        else:
            print_text=my_text
        if not self._lookup_mode:
            print(print_text)

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

class KSPart(object):
    _name=None
    _path=None
    _translate_extractor=None
    _translate=None
    _vars=None

    def __init__(self,path):
        self._name=os.path.basename(path)
        self._path=path
        self._translate_extractor=re.compile(r'@@(\w+)@@')
        self._translate=False
        self._vars=set()

    def setTranslate(self,translate):
        self._translate=translate

    def getName(self):
        return self._name

    def setName(self,name):
        """Changes name AND renames corresponding file"""
        dir_path=os.path.dirname(self._path)
        new_path=os.path.join(dir_path,name)
        if os.path.islink(self._path):
            # we need to fix the source too...?
            pass
        os.rename(self._path,new_path)
        self._name=name
        self._path=new_path

    def getPath(self):
        return self._path

    path=property(getPath)
    name=property(getName,setName)

    def _translator(self,my_text):
        sub_vars=self.listVars(my_text)
        for sv in sub_vars:
            self._vars.add(sv)
        # print(sub_vars)
        res_text=my_text
        for my_var in sub_vars:
            my_sub=self._var_lookup(my_var)
            if not my_sub is None:
                res_text=re.sub('@@'+my_var+'@@',my_sub,res_text)
        return res_text

    def lines(self):
        f=open(self._path,'r')
        for l in f:
            if self._translate:
                yield self._translator(l)
            else:
                yield l
        f.close()

    def getVars(self):
        return self._vars

    def listVars(self,my_text):
        return self._translate_extractor.findall(my_text)

    def scanVars(self):
        for l in self.lines():
            pre_vars=self._translate_extractor.findall(l)
            for v in pre_vars:
                self._vars.add(v)
        return self._vars


    def _var_lookup(self,var):
        if os.environ.has_key(var):
            return os.environ[var]
        else:
            return None


class KSPartL(KSPart):
    _orig_path=None
    def __init__(self,path,orig_path):
        super(KSPartL,self).__init__(path)
        # self._orig_path=os.readlink(path)
        self._orig_path=orig_path

    def materialize(self):
        my_dir=os.path.dirname(self._path)
        src_path=os.path.relpath(self._orig_path,my_dir)
        os.symlink(src_path,self._path)

    def getOrigPath(self):
        return self._orig_path

    def setOrigPath(self,new_orig_path):
        # we're changing origin here...
        # 1. remove existing link
        # 2. link to new target based on name and path
        my_dir=os.path.dirname(self._path)
        os.unlink(self._path)

        os.symlink(os.path.relpath(new_orig_path,my_dir),self._path)
        # src_part=os.path.join(os.path.relpath(parts_dir,os.path.join(template_dir,p)),p,pe)

    orig_path=property(getOrigPath,setOrigPath)

class KSPartsDB(object):
    _db=None
    _path=None
    _blacklist=None
    _translate=None

    def __init__(self,path,blacklist=[],translate=False):
        self._db={}
        self._path=path
        self._blacklist=blacklist
        self._translate=translate

    def load(self):
        for s in SECTIONS:
            s_path=os.path.join(self._path,s)
            if not self._db.has_key(s):
                self._db[s]={}
            for pn in os.listdir(s_path):
                if not pn in self._blacklist:
                    new_part=KSPart(os.path.join(s_path,pn))
                    new_part.setTranslate(self._translate)
                    self._db[s][pn]=new_part

    def setTranslate(self,translate):
        self._translate=translate

    def setTranslateAll(self,translate):
        for s in self._db.keys():
            for p in self._db[s].keys():
                self._db[s][p].setTranslate(translate)
        self._translate=translate

    def getBlacklist(self):
        return self._blacklist

    def setBlacklist(self,blacklist):
        self._blacklist=blacklist

    blacklist=property(getBlacklist,setBlacklist)

    def getDB(self):
        return self._db

    db=property(getDB)

    def __getitem__(self,k):
        return self._db[k]

class KSTemplate(object):
    # Dictionary with parts divided into sections
    _parts=None
    # template ID
    _name=None
    _path=None
    def __init__(self,template_id,path):
        self._name=template_id
        self._parts={}
        self._path=path

    def load(self):
        for s in SECTIONS:
            self._parts[s]={}
            s_path=os.path.join(self._path,s)
            for p in os.listdir(s_path):
                p_path=os.path.join(s_path,p)
                self._parts[s][p]=KSPartL(p_path,os.path.realpath(p_path))

    def init(self):
        template_dir=self._path
        def _my_mkdir(my_dir):
            try:
                os.makedirs(my_dir)
            except OSError:
                # very crude, should handle errorcode instead:
                # OSError: [Errno 17] File exists: '
                pass
        for s in SECTIONS:
            _my_mkdir(os.path.join(template_dir,s))
            if not self._parts.has_key(s):
                self._parts[s]={}

    def addPart(self,section,part):
        template_dir=self._path
        name=part.name
        section_dir=os.path.join(template_dir,section)
        tpart_path=os.path.join(section_dir,name)

        p=KSPartL(tpart_path,part.path)
        p.materialize()
        self._parts[section][name]=p

    def getParts(self):
        return self._parts

    parts=property(getParts)

class KSTemplateDB(object):
    _db=None
    _path=None
    def __init__(self,path):
        self._db={}
        self._path=path

    def load(self):
        for t in os.listdir(self._path):
            kst=KSTemplate(t,os.path.join(self._path,t))
            kst.load()
            self._db[t]=kst

    def newTemplate(self,template_id):
        return KSTemplate(template_id,os.path.join(self._path,template_id))

    def getDB(self):
        return self._db

    db=property(getDB)

    def __getitem__(self,k):
        return self._db[k]

class Conveyor(object):
    _parts=None
    _templates=None

    def __init__(self,parts_path='parts',parts_blacklist=[],parts_translate=False,templates_path='templates'):
        self._parts=KSPartsDB(parts_path,parts_blacklist,parts_translate)
        self._parts.load()
        self._templates=KSTemplateDB(templates_path)
        self._templates.load()

    def renamePart(self,section,src_name,dst_name):
        ## Need to find out part's parent... hmm...
        ## also need to trace part in all templates
        part=self._parts[section][src_name]
        part.name=dst_name
        print(part.path)
        for tid in self._templates.db.keys():
            template=self._templates[tid]
            if template.parts[section].has_key(src_name):
                lpart=template.parts[section][src_name]
                print(lpart.path,lpart.orig_path)
                lpart.name=dst_name
                lpart.setOrigPath(part.path)

    def addPart(self,template_id,section,name):
        part=self._parts[section][name]
        template=self._templates[template_id]
        template.addPart(section,part)

    def getParts(self):
        return self._parts

    def getTemplates(self):
        return self._templates

    parts=property(getParts)
    templates=property(getTemplates)

class KSAssembler(object):
    _base_dir=None
    _ignore_dirs=None
    _translate=None
    _conveyor=None

    def __init__(self,base_dir,ignore_dirs):
        self._base_dir=base_dir
        self._ignore_dirs=ignore_dirs
        self._translate=False
        templates_dir=os.path.join(self._base_dir,'templates')
        parts_dir=os.path.join(self._base_dir,'parts')
        self._conveyor=Conveyor(parts_dir,self._ignore_dirs,templates_dir)


    def setTranslate(self,trans):
        self._translate=trans
        self._conveyor.parts.setTranslateAll(trans)

    def setup(self,template_id):
        t=self._conveyor.templates.newTemplate(template_id)
        t.init()
        self._conveyor.templates.db[template_id]=t

    def listparts(self):
        cat=Cat()
        cat.setTranslate(self._translate)
        for s in SECTIONS:
            for pn in self._conveyor.parts[s].keys():
                cat.echo(s + ' ' + pn)

    def create(self,template_id,parts):
        # create FS layout
        self.setup(template_id)

        for s in SECTIONS:
            if not parts.has_key(s):
                continue
            for p in parts[s]:
                part=self._conveyor.parts[s][p]
                self._conveyor.templates[template_id].addPart(s,part)

    def clone(self,src_template_id,dst_template_id):
        pass

    def assemble(self,template_id,pkg_opts,var_summary=False,dry_run=False):
        template=self._conveyor.templates[template_id]
        ks_commands=template.parts['commands']
        ks_packages=template.parts['packages']
        ks_pre=template.parts['pre']
        ks_post=template.parts['post']
        ks_post_header=template.parts['post.header']

        ignore_dirs=self._ignore_dirs
        cat=Cat()
        cat.setTranslate(self._translate)
        sub_cat=Cat()
        sub_cat.setTranslate(self._translate)
        cat.setIgnoreDirs(ignore_dirs)
        if dry_run:
            if var_summary:
                all_vars=set()
                for s in template.parts.keys():
                    for p in template.parts[s].keys():
                        for v in template.parts[s][p].scanVars():
                            all_vars.add(v)
                cat.echo("## Seen vars:\n# "+"\n# ".join(all_vars))
                return
            # cat.setLookupMode(True)
            sub_cat.setLookupMode(True)

        
        ###XXX Have to simplify below... Cat is no longer
        ###XXX required to be smart
        cat.echo("## Auto-generated by conveyor line")
        def cat_parts(my_parts,the_cat=cat):
            for k in my_parts.keys():
                my_part=my_parts[k]
                the_cat(my_part.path)

        cat_parts(ks_commands)

        cat.echo("\n%packages "+pkg_opts)
        cat_parts(ks_packages)
        cat.echo("%end\n")

        cat.setPreamble("\n%pre")
        cat.setPS("%end\n")
        cat_parts(ks_pre)

        cat.setDecor(DECOR_FILE)
        def post_header(x):
            if x & DECOR_FILE:
                cat_parts(ks_post_header,sub_cat)
        cat.setHeaderCall(post_header)
        cat.setPreamble("\n%post --erroronfail --log=/root/anaconda-{file_basename}.log")
        cat_parts(ks_post)
        cat.resetDecor()

        if var_summary:
            all_vars=set()
            for s in template.parts.keys():
                for p in template.parts[s].keys():
                    for v in template.parts[s][p].getVars():
                        all_vars.add(v)
            cat.echo("## Seen vars:\n# "+"\n# ".join(all_vars))

class RawAssembler(object):
    _base_dir=None
    _ignore_dirs=None
    _translate=None

    def __init__(self,base_dir,ignore_dirs):
        self._base_dir=base_dir
        self._ignore_dirs=ignore_dirs
        self._translate=False

    def setTranslate(self,trans):
        self._translate=trans

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
        cat.setTranslate(self._translate)
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
        cat.setTranslate(self._translate)
        # create FS layout
        self.setup(template_id)

        # for p in parts.keys():
        for p in SECTIONS:
            # walking through sections: commands,packages,pre,post,post.header
            if not parts.has_key(p):
                continue
            for pe in parts[p]:
                dst_part=os.path.join(template_dir,p,pe)
                src_part=os.path.join(os.path.relpath(parts_dir,os.path.join(template_dir,p)),p,pe)
                try:
                    os.symlink(src_part,dst_part)
                except OSError:
                    print("Can't link {1} to {0}, skipping".format(src_part,dst_part))

    def clone(self,src_template_id,dst_template_id):
        pass

    def assemble(self,template_id,pkg_opts,var_summary=False,dry_run=False):
        template_dir=os.path.join(self._base_dir,'templates',template_id)
        ks_commands=os.path.join(template_dir,'commands')
        ks_packages=os.path.join(template_dir,'packages')
        ks_pre=os.path.join(template_dir,'pre')
        ks_post=os.path.join(template_dir,'post')
        ks_post_header=os.path.join(template_dir,'post.header')

        ignore_dirs=self._ignore_dirs
        cat=Cat()
        cat.setTranslate(self._translate)
        sub_cat=Cat()
        sub_cat.setTranslate(self._translate)
        cat.setIgnoreDirs(ignore_dirs)
        if dry_run:
            cat.setLookupMode(True)
            sub_cat.setLookupMode(True)

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

        if dry_run:
            sumvar_cat=Cat()
        else:
            sumvar_cat=cat
        if var_summary:
            sumvar_cat.echo("## Seen vars:\n# "+"\n# ".join(cat.seenVars().union(sub_cat.seenVars())))

Assembler=KSAssembler

if __name__ == '__main__':
    parser=argparse.ArgumentParser()

    parser.add_argument('--base-dir','-b',type=str,help='',default='.')
    parser.add_argument('--ignore-dirs','-i',type=str,help='',default='RCS')
    subparsers=parser.add_subparsers(dest='command',help='')

    parser_assemble=subparsers.add_parser('assemble')
    parser_assemble.add_argument('--template-id','-t',type=str,help='',required=True,default=None)
    parser_assemble.add_argument('--packages-opts','-o',type=str,help='',default='--nobase')
    parser_assemble.add_argument('--translate',action='store_const', const=True,default=False,help='')
    parser_assemble.add_argument('--list-vars',action='store_const', const=True,default=False,help='')
    parser_assemble.add_argument('--dry-run',action='store_const', const=True,default=False,help='')

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
        a.setTranslate(args.translate)
        a.assemble(args.template_id,args.packages_opts,var_summary=args.list_vars,dry_run=args.dry_run)
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

