Intro
=====

Conveyor belt for Fedora/RedHat Kickstart file production. 

This tool aims to help in creation and maintenance of KS templates
based on common "parts".

Sample FS structure::

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

Sample use
==========

Querying
--------

List all templates, their parts and vars used::

  $ ksconveyor.py lstemplates --list-vars --list-parts

List all templates starting with 'bare'::

  $ ksconveyor.py lstemplates --list-vars --list-part bare


New templates
-------------

From scratch
~~~~~~~~~~~~

Init::

  $ ksconveyor.py init -t my-new-template

Add parts to section "%pre"::

  $ ksconveyor.py addpart -S pre -p part1,part2,part3

Fom a copy
~~~~~~~~~~

Copy "baremetal" template to "vm" template::

  ksconveyor.py clone -s baremetal -d vm


Manipulating templates
----------------------

Rename part (it will rename all references too)::

  $ ksconveyor.py mvpart -S pre -s part1 -d default-pre

Add part to existing template::

  $ ksconveyor.py addpart -S pre -p part1,part2,part3

Remove parts from template
~~~~~~~~~~~~~~~~~~~~~~~~~~

Removal was not implemented deliberately. Operation is simply a::

  $ unlink <BASE_DIR>/templates/<template_id>/<section>/<part_name>


