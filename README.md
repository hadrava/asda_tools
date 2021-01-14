# ASDA tools

Simple Python3 parser for `.par` files produced by ASDASoft by Delta
Electronics. Main purpose of this tool is to help with comparing servo driver
configuration backups using 'normal' tools such as `vimdiff`.

It can also be used as an diff-tool for git, so you will get human-readable git
diffs while commiting raw binary `.par` files to your repository.

## Warning
This was tested only on a few files produced by ASDASoft version 5.4.1.0 with
ASDA-A2 servo driver. Implementation may be incomplete for other series.

On the other hand, this script tries to work on the safe side - if it produces
json output without giving any error, then you can be sure, that it can
completely recreate original `.par` file from this json.

This script was created by examination of few `.par` files. The script is most
probably not complete. If you find that it fails on any `.par` file produced by
ASDASoft, feel free to create new issue and please include that `.par` file.
(You will probably need to zip it before Github will accept it.)

## Using as git diff-tool

TODO
