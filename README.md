# README

This is the beginning of an effort to develop a set of more polished, reusable and maintanable scripts and tools for automating common tasks in UCR Special Collections & University Archives.

* **oac_process.py** is a command-line tool that takes one or more EAD files exported with ArchivesSpace defaults and tidies them up according to local guidelines. It also validates against the EAD schema to alert to any errors or issues. The resulting file is an EAD file ready for upload to OAC.

**Example**
`python oac_process.py "C:\Users\ngeraci\Downloads\UA.398_20180424_193147_UTC__ead.xml"`

Output:
`EAD validated
ua398.xml processing completed`