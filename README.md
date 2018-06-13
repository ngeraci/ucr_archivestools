# UCR archives tools

This is the beginning of an effort to develop a set of more polished, reusable and maintanable scripts and tools for automating common tasks in UCR Special Collections & University Archives (and adjacent work in technical services and digital initiatives).

If you work at UCR Library, more detailed documentation on setup and usage is on our [local wiki](https://libwiki.ucr.edu/display/CSCD/SCUA+Python+tools). If you don't work at UCR Library, it's unlikely that these tools will be directly useful to you, but could potentially serve as a reference for getting started writing code and building command-line tools in an archives context.

## oac-process
**oac-process** is a command-line tool that takes one or more EAD files exported with ArchivesSpace defaults and tidies them up according to local guidelines. It validates the EAD to alert to any errors or issues. The resulting file is an EAD file ready for upload to OAC.

Its default behavior also moves the files to standard locations on the UCR Library shared drive.

**Example**:

`oac-process UA.398_20180424_193147_UTC__ead.xml`

**Output**:
````
EAD validated
ua398.xml processing completed
````

**Note**: The default of moving the file to the shared drive will **overwrite** any existing file with the same name. If you don't want this, use the option `--in-place`.

### Usage & options
```
usage: oac-process [-h] [--wrca] [--in-place] [--keep-raw] [files [files ...]]

positional arguments:
  files       one or more files to process

optional arguments:
  -h, --help  show this help message and exit
  --wrca      use --wrca when processing WRCA file(s).
  --in-place  use --in-place if you want to process the file where it is,
              instead of moving it to the standard shared drive location
  --keep-raw  use --keep-raw if you want to keep the original file(s)
              downloaded from ArchivesSpace. Otherwise, they'll be deleted.
```
Optional arguments work like this: `oac-process --wrca MS.20106_20180607_000126_UTC__ead.xml`

**To process more than one file at a time**, simply list them separated by spaces:

`oac-process MS.052_20180424_194135_UTC__ead.xml UA.365_20180424_194010_UTC__ead.xml`

They'll be processed in sequential order.

