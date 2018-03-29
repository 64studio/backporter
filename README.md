backporter
==========

A Free Software tool used by 64 Studio Ltd. to backport bleeding edge packages for stable GNU/Linux distributions.

Backporter is a job scheduler for [rebuildd](https://packages.debian.org/search?keywords=rebuildd). It monitors a configurable set of APT source URIs, typically referring to bleeding edge suites like Debian sid, and checks for newer versions of the packages one wants to backport. If newer versions are found it tries to built them against other suites (typically released ones, like Debian stable).

You can browse the source code at https://github.com/64studio/backporter

----

Documentation

----

backporter help *topic*

List available commands, where *topic* is one of:

   list

   add

   remove

   set

   source

   status

   update

   schedule

----

backporter list [-d *dist*]

Show current backports for distribution *dist*

----

backporter add [-d *dist*] *pkg*

Add a backport of package *pkg* for distribution *dist*

----

backporter remove [-d *dist*] *pkg*

Remove a backport of package *pkg* from distribution *dist*

----

backporter set [-d *dist*] *pkg* policy Never|Once|Always|Smart

Set backport policy options on package *pkg* for distribution *dist*

----

backporter set [-d *dist*] *pkg* origin 64studio|sid|karmic|medibuntu

Set backport upstream origin (from known parent distros) on package *pkg* for distribution *dist*

----

backporter source -d *dist* *pkg*=version [-- *apt-get options*]

Download and repack a source package *pkg* for distribution *dist*

----

backporter status [-d *dist*]

Show backport job status

----

backporter update

Update package versions from APT sources in /etc/backporter.conf

----

backporter schedule

Schedule new backport jobs

