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

Each part can contain "variables" - set of characters enclused in '@@', like so::
  
  ...
  mkdir @@DATADIR@@/my_dir
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

From a copy
~~~~~~~~~~~

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

Generating KickStart
--------------------

Simple invocation, which assumes you'll be modifying kickstart manually replacing all vars. Assemble Kickstart using "baremetal" template, list all encountered vars in the header and save into '../servers/server1.ks'::

  $ ./ksconveyor.py assemble -t baremetal --list-all-vars > ../servers/server1.ks

More advanced use. Substitute encountered vars with their value from Environment variables::

  $ DATADIR=/root/ks_dir ./ksconveyor.py assemble -t baremetal --translate --list-all-vars > ../servers/server1.ks

Lets crank it up a notch and exclude one part ('pre:part1') that we think is not needed for the server1::

  $ DATADIR=/root/ks_dir ./ksconveyor.py assemble -t baremetal -x pre:part1 --translate --list-all-vars > ../servers/server1.ks

Now lets add a part that is not currently part of template::

  $ DATADIR=/root/ks_dir ./ksconveyor.py assemble -t baremetal -e post:optional -x pre:part1 --translate --list-all-vars > ../servers/server1.ks

Notes
~~~~~

After kickstart has been generated - go over it carefully and make sure it does what you think it should. You will notice that header contains all necessary information to re-create this template, in most scenarios that is the information you want to use to create similar kickstart rather than taking a copy of generated one. After all - some parts may have been updated to include up-to-date info etc. and you don't want to fix those manually after the install (or during!)

