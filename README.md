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

All the parsing is located in a single script `asda_tools/asdapar2json.py` and
it has no special dependency. So you can copy it to your repository. (Let's
assume, it will be in the same place as in this repository, inside `asda_tools`
directory.)


Then you need to asociate `.par` files with new difftool by creating a
`.gitattributes` with content:
```
*.par diff=asdapar2json
```

And lastly, you need to enable this script in every clone of your repository.

**That is security measure** -- script will be run automatically by git in the
background. It might be better idea to have script somewhere outside of the
repository and update it manually. Otherwise **mallicious version can be run by
git when you switch to branch from untrusted source!**

But it should be safe in case of your private repository.

In that case, just add:

```
[diff "asdapar2json"]
	textconv = `git rev-parse --show-toplevel`/asda_tools/asdapar2json.py
```
to the file `.git/config`.


If you are brave enough to run my version, you can test it on this repository :)

Just clone it, edit the `.git/config` and run:
```
git log -p test/test_files/test_01_pr.par
```
