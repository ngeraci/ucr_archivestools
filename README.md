# README

This is the beginning of an effort to develop a set of more polished, reusable and maintanable scripts and tools for automating common tasks in UCR Special Collections & University Archives.
## oac_process
**oac_process.py** is a command-line tool that takes one or more EAD files exported with ArchivesSpace defaults and tidies them up according to local guidelines. It also validates against the EAD schema to alert to any errors or issues. The resulting file is an EAD file ready for upload to OAC.

**Example**:
Run the command `python oac_process.py "C:\Users\ngeraci\Downloads\UA.398_20180424_193147_UTC__ead.xml"` 

**Output**: 
````
EAD validated
ua398.xml processing completed
````
The original export has been replaced by the processed file.

**To process more than one file at a time**, simply list them separated by spaces:

`python oac_process.py "C:\Users\ngeraci\Downloads\MS.052_20180424_194135_UTC__ead.xml" "C:\Users\ngeraci\Downloads\UA.365_20180424_194010_UTC__ead.xml"`

They'll be processed in sequential order.

