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


SECTIONS=('commands','packages','pre','post','post.header')

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
        my_vars=list(self._vars)
        my_vars.sort()
        return my_vars

    def varSubs(self):
        if self._vars:
            my_vars=self._vars
        else:
            my_vars=self.scanVars()

        subs={}
        for v in my_vars:
            lv=self._var_lookup(v)
            if lv:
                subs[v]=lv
        return subs
        
    def listVars(self,my_text):
        my_vars=self._translate_extractor.findall(my_text)
        my_vars.sort()
        return my_vars

    def scanVars(self):
        for l in self.lines():
            pre_vars=self._translate_extractor.findall(l)
            for v in pre_vars:
                self._vars.add(v)
        my_vars=list(self._vars)
        my_vars.sort()
        return my_vars


    def _var_lookup(self,var):
        if os.environ.has_key(var):
            return os.environ[var]
        else:
            return None

class KSPartL(KSPart):
    """Link to the original part. Behaves like a normal KSPart, only
    stores link to the original and can "materialize" """
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
        self._orig_path=new_orig_path

    orig_path=property(getOrigPath,setOrigPath)

class KSPartV(KSPartL):
    """Virtual part, needed for ad-hoc parts addition. Somewhat evil hacked"""
    def __init__(self,path,orig_path):
        """call ancestor and ignore non-essential stuff"""
        # We'll ignore path relative to template... just store
        # origin's path
        super(KSPartV,self).__init__(orig_path,orig_path)

    def materialize(self):
        """Materialize the link... not really important for this subclass"""
        # We can't meterialize something that's virtual
        pass

    def setOrigPath(self,new_orig_path):
        """Change the path to the origin. Should not really need it, but "just in case" """
        self._orig_path=new_orig_path

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
            pn_list=os.listdir(s_path)
            pn_list.sort()
            for pn in pn_list:
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
            p_list=os.listdir(s_path)
            p_list.sort()
            for p in p_list:
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

    def detachPart(self,section,part_name):
        """Detach part from in-memory instance of template only.
        Useful for quick manipulations.
        Changes are not transfered to disk"""
        del self._parts[section][part_name]

    def attachPart(self,section,part,part_type=KSPartL):
        """Attach part to in-memory instance only.
        Useful for quick manipulation. Can only take parts
        subclassed from KSPartL"""
        template_dir=self._path
        name=part.name
        section_dir=os.path.join(template_dir,section)
        tpart_path=os.path.join(section_dir,name)
        p=part_type(tpart_path,part.path)
        self._parts[section][name]=p
        return p

    def addPart(self,section,part,part_type=KSPartL):
        """Attach part and make it persitant. Can only take parts
        subclassed from KSPartL"""
        self.attachPart(section,part,part_type)
        p=self._parts[section][part.name]
        p.materialize()
        return p

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
        t_list=os.listdir(self._path)
        t_list.sort()
        for t in t_list:
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

    def setTranslateAll(self,translate):
        for t in self._db.keys():
            for s in self._db[t].parts.keys():
                for k in self._db[t].parts[s].keys():
                    self._db[t].parts[s][k].setTranslate(translate)

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
        self._conveyor.templates.setTranslateAll(trans)

    def setup(self,template_id):
        t=self._conveyor.templates.newTemplate(template_id)
        t.init()
        self._conveyor.templates.db[template_id]=t

    def lsparts(self,list_vars=False):
        for s in SECTIONS:
            pn_list=self._conveyor.parts[s].keys()
            pn_list.sort()
            for pn in pn_list:
                part=self._conveyor.parts[s][pn]
                if list_vars:
                    p_vars=part.scanVars()
                    if p_vars:
                        p_vars.sort()
                        vars_txt=" ( {0} )".format(" ".join(p_vars))
                    else:
                        vars_txt=""
                else:
                    vars_txt=""
                print(s + ' ' + pn+vars_txt)

    def lstemplates(self,filter=None,list_parts=False,list_vars=False,list_all_parts=False):
        if filter:
            re_filter=re.compile(filter)
        for t in self._conveyor.templates.db.keys():
            if filter:
                if not re_filter.search(t):
                    continue
            if list_parts:
                print(t)
                template=self._conveyor.templates[t]
                all_parts={}
                if list_all_parts:
                    for s in self._conveyor.parts.db.keys():
                        all_parts[s]=set()
                        for p in self._conveyor.parts[s].keys():
                            all_parts[s].add(p)
                for s in SECTIONS:
                    #for s in template.parts.keys():
                    if template.parts.has_key(s):
                        p_list=template.parts[s].keys()
                        p_list.sort()
                    else:
                        p_list=[]
                    for p in p_list:
                        if list_all_parts:
                            all_parts[s].remove(p)
                        if list_vars:
                            p_vars=template.parts[s][p].scanVars()
                            if p_vars:
                                p_vars_sort=list(p_vars)
                                p_vars_sort.sort()
                                vars_txt=" ( {0} )".format(" ".join(p_vars_sort))
                            else:
                                vars_txt=""
                        else:
                            vars_txt=""
                        print('  ++ '+s+' '+p+vars_txt)
                    if all_parts.has_key(s):
                        for p in all_parts[s]:
                            if list_vars:
                                p_vars=self._conveyor.parts[s][p].scanVars()
                                if p_vars:
                                    p_vars_sort=list(p_vars)
                                    p_vars_sort.sort()
                                    vars_txt=" ( {0} )".format(" ".join(p_vars_sort))
                                else:
                                    vars_txt=""
                            else:
                                vars_txt=""
                            print('  -- '+s+' '+p+vars_txt)
            elif list_vars:

                template=self._conveyor.templates[t]
                all_vars=set()
                for s in SECTIONS:
                    #for s in template.parts.keys():
                    if template.parts.has_key(s):
                        p_list=template.parts[s].keys()
                        p_list.sort()
                    else:
                        p_list=[]
                    for p in p_list:
                        p_vars=template.parts[s][p].scanVars()
                        for pv in p_vars:
                            all_vars.add(pv)
                if all_vars:
                    all_vars_sorted=list(all_vars)
                    all_vars_sorted.sort()
                    all_vars_txt=" ( {1} )".format(t, " ".join(all_vars_sorted))
                else:
                    all_vars_txt=""
                print("{0}{1}".format(t, all_vars_txt))
            else:
                print(t)

    def create(self,template_id,parts):
        # create FS layout
        self.setup(template_id)

        for s in SECTIONS:
            if not parts.has_key(s):
                continue
            for p in parts[s]:
                part=self._conveyor.parts[s][p]
                self._conveyor.templates[template_id].addPart(s,part)

    def addpart(self,template_id,section,parts):
        for part_id in parts:
            self._conveyor.addPart(template_id,section,part_id)

    def mvpart(self,section,src_part_id,dst_part_id):
        self._conveyor.renamePart(section,src_part_id,dst_part_id)

    def clone(self,src_template_id,dst_template_id):
        template=self._conveyor.templates[src_template_id]
        self.setup(dst_template_id)
        for s in template.parts.keys():
            section=template.parts[s]
            for p in section.keys():
                part=self._conveyor.parts[s][p]
                self._conveyor.templates[dst_template_id].addPart(s,part)


    def assemble(self,template_id,pkg_opts,var_summary=False,dry_run=False,extra_parts=None,exclude_parts=None,legacy_mode=False):
        template=self._conveyor.templates[template_id]
        ks_commands=template.parts['commands']
        ks_packages=template.parts['packages']
        ks_pre=template.parts['pre']
        ks_post=template.parts['post']
        ks_post_header=template.parts['post.header']

        if extra_parts:
            for s in extra_parts.keys():
                for p in extra_parts[s]:
                    part=self._conveyor.parts[s][p]
                    template.attachPart(s,part,part_type=KSPartV)
                    new_part=template.parts[s][p]
                    new_part.setTranslate(self._translate)

        if exclude_parts:
            for s in exclude_parts.keys():
                for p in exclude_parts[s]:
                    template.detachPart(s,p)

        print("## Auto-generated by conveyor line\n")
        print("##TEMPLATE: "+template_id)
        if extra_parts:
            print("##EXTRAS: "+"{0}".format(" ".join(["{0}:{1}".format(s,",".join(extra_parts[s])) for s in extra_parts.keys()])))
        if exclude_parts:
            print("##EXCLUDES: "+"{0}".format(" ".join(["{0}:{1}".format(s,",".join(exclude_parts[s])) for s in exclude_parts.keys()])))

        print("##LEGACY MODE: {0}".format("On" if legacy_mode else "Off"))
        print("")

        ignore_dirs=self._ignore_dirs
        all_vars_s=set()
        for s in template.parts.keys():
            for p in template.parts[s].keys():
                for v in template.parts[s][p].scanVars():
                    all_vars_s.add(v)
        all_vars=list(all_vars_s)
        all_vars.sort()
        if var_summary:
            print("##All vars: "+" ".join(all_vars))

        if dry_run:
            return

        
        if self._translate:
            remaining_vars=all_vars_s
            vars_summary={}
            for s in template.parts.keys():
                for p in template.parts[s].keys():
                    p_vars=template.parts[s][p].varSubs()
                    vars_summary.update(p_vars)
            print("##Supplied vars: {0}".format(' '.join(["{0}=\"{1}\"".format(k,vars_summary[k]) for k in vars_summary.keys()])))
            for v in vars_summary.keys():
                remaining_vars.remove(v)
            remaining_vars_list=list(remaining_vars)
            remaining_vars_list.sort()
            print("##Remaining vars: {0}\n".format(" ".join(remaining_vars_list)))

        def cat(my_parts,section_name=None):
            my_parts_keys=my_parts.keys()
            my_parts_keys.sort()
            if section_name:
                s_name=section_name+':'
            else:
                s_name=''
            for k in my_parts_keys:
                my_part=my_parts[k]
                print('##PART: {0}{1}'.format(s_name,my_part.name))
                for l in my_part.lines():
                    print(l,end='')
                # the_cat(my_part.path)

        cat(ks_commands,'commands')

        print("\n%packages "+pkg_opts)
        cat(ks_packages,'packages')
        if not legacy_mode: print("%end\n")

        ks_pre_keys=ks_pre.keys()
        ks_pre_keys.sort()
        for k in ks_pre_keys:
            my_pre=ks_pre[k]
            print("\n%pre")
            print('##PART: pre:{0}'.format(my_pre.name))
            for l in my_pre.lines():
                print(l,end='')
            if not legacy_mode: print("\n%end")

        ks_post_keys=ks_post.keys()
        ks_post_keys.sort()
        for k in ks_post_keys:
            my_post=ks_post[k]
            print("\n%post --erroronfail --log=/root/anaconda-"+k+".log")
            cat(ks_post_header,'post.header')
            print('##PART: post:{0}'.format(my_post.name))
            for l in my_post.lines():
                print(l,end='')
            if not legacy_mode: print("\n%end")


Assembler=KSAssembler

if __name__ == '__main__':
    parser=argparse.ArgumentParser()

    parser.add_argument('--base-dir','-b',type=str,help='Conveyor belt location',default='.')
    parser.add_argument('--ignore-dirs','-i',type=str,help='List of directories/files to ignore',default='RCS')
    subparsers=parser.add_subparsers(dest='command',help='Sub-commands')

    parser_assemble=subparsers.add_parser('assemble',help='process template sending resulting KS to stdout')
    parser_assemble.add_argument('--template-id','-t',type=str,help='Template ID',required=True,default=None)
    parser_assemble.add_argument('--packages-opts','-o',type=str,help='Options to pass to %%packages macro',default='--nobase')
    parser_assemble.add_argument('--extra-parts','-e',type=str,help='Extra parts in format: "section1:partA,partB;section2:partD',required=False,default=None)
    parser_assemble.add_argument('--exclude-parts','-x',type=str,help='Exclude parts in format: "section1:partA,partB;section2:partD',required=False,default=None)
    parser_assemble.add_argument('--translate',action='store_const', const=True,default=False,help='Translate/extract meta-vars in parts (Using @@VAR@@ form and $VAR environment variable)')
    parser_assemble.add_argument('--list-all-vars',action='store_const', const=True,default=False,help='Also list all available meta-vars')
    parser_assemble.add_argument('--dry-run',action='store_const', const=True,default=False,help="Don't perform any real action")
    parser_assemble.add_argument('--legacy-mode',action='store_const', const=True,default=False,help="Legacy mode: disable newer features of Anaconda, like %end tags etc.")

    parser_assemble=subparsers.add_parser('init',help='Initialize template FS structure')
    parser_assemble.add_argument('--template-id','-t',type=str,help='Template ID',required=True,default=None)

    parser_assemble=subparsers.add_parser('addpart',help="Add parts to template's section")
    parser_assemble.add_argument('--template-id','-t',type=str,help='Template ID',required=True,default=None)
    parser_assemble.add_argument('--section','-S',type=str,help='Kisctart Section name (commands,packages,etc.)',required=True,default=None)
    parser_assemble.add_argument('--parts','-p',type=str,help='List of comma-separated parts',required=True,default=None)

    parser_assemble=subparsers.add_parser('mvpart',help='Rename part')
    parser_assemble.add_argument('--section','-S',type=str,help='Kickstart Section name (commands,packages,etc.)',required=True,default=None)
    parser_assemble.add_argument('--src','-s',type=str,help='Current part name',required=True,default=None)
    parser_assemble.add_argument('--dst','-d',type=str,help='New part name',required=True,default=None)

    parser_assemble=subparsers.add_parser('lsparts',help='List all available parts')
    parser_assemble.add_argument('--list-vars',action='store_const', const=True,default=False,help='Include meta-variable information')

    parser_assemble=subparsers.add_parser('lstemplates',help='List all available templates')
    parser_assemble.add_argument('--list-parts',action='store_const', const=True,default=False,help='List template parts')
    parser_assemble.add_argument('--list-vars',action='store_const', const=True,default=False,help='List used meta-vars')
    parser_assemble.add_argument('--list-all-parts',action='store_const', const=True,default=False,help='List all available parts for every template, highlight the ones used')
    parser_assemble.add_argument('filter', type=str, nargs='?', default=None, help='Regexp filter')

    parser_assemble=subparsers.add_parser('clone',help='Clone existing template')
    parser_assemble.add_argument('--src-template-id','-s',type=str,help='Existing template name',required=True,default=None)
    parser_assemble.add_argument('--dst-template-id','-d',type=str,help='New template name',required=True,default=None)

    parser_assemble=subparsers.add_parser('create',help='Create new template')
    parser_assemble.add_argument('--template-id','-t',type=str,help='Template ID',required=True,default=None)
    for s in SECTIONS:
        parser_assemble.add_argument('--'+s,type=str,help='',required=True,default=None)

    args=parser.parse_args(sys.argv[1:])
    ignore_dirs=args.ignore_dirs.split(',')
    if args.command == 'assemble':
        a=Assembler(args.base_dir,ignore_dirs)
        a.setTranslate(args.translate)

        if args.extra_parts:
            extra_parts={}
            s_chunks=args.extra_parts.split(';')
            for s_str in s_chunks:
                s_chunks_split=s_str.split(':')
                s=s_chunks_split[0]
                part_chunks=s_chunks_split[1].split(',')
                extra_parts[s]=[]
                for p in part_chunks:
                    extra_parts[s].append(p)
        else:
            extra_parts=None

        if args.exclude_parts:
            exclude_parts={}
            s_chunks=args.exclude_parts.split(';')
            for s_str in s_chunks:
                s_chunks_split=s_str.split(':')
                s=s_chunks_split[0]
                part_chunks=s_chunks_split[1].split(',')
                exclude_parts[s]=[]
                for p in part_chunks:
                    exclude_parts[s].append(p)
        else:
            exclude_parts=None

        a.assemble(args.template_id,
                   args.packages_opts,
                   var_summary=args.list_all_vars,
                   dry_run=args.dry_run,
                   extra_parts=extra_parts,
                   exclude_parts=exclude_parts,
                   legacy_mode=args.legacy_mode)
    elif args.command=='init':
        a=Assembler(args.base_dir,ignore_dirs)
        a.setup(args.template_id)
    elif args.command=='mvpart':
        a=Assembler(args.base_dir,ignore_dirs)
        a.mvpart(args.section,args.src,args.dst)
    elif args.command=='addpart':
        a=Assembler(args.base_dir,ignore_dirs)
        a.addpart(args.template_id,args.section,args.parts.split(','))
    elif args.command=='lsparts':
        a=Assembler(args.base_dir,ignore_dirs)
        a.lsparts(args.list_vars)
    elif args.command=='lstemplates':
        a=Assembler(args.base_dir,ignore_dirs)
        a.lstemplates(args.filter,args.list_parts,args.list_vars,args.list_all_parts)
    elif args.command=='clone':
        a=Assembler(args.base_dir,ignore_dirs)
        a.clone(args.src_template_id,args.dst_template_id)
    elif args.command=='create':
        a=Assembler(args.base_dir,ignore_dirs)
        my_parts={}
        vargs=vars(args)
        for s in SECTIONS:
            my_parts[s]=vargs[s].split(',')
        a.create(args.template_id,my_parts)

