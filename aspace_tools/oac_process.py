#!/usr/bin/env python

"""A command line tool for cleaning up EAD files at UCR.

This tool performs a standard set of edits on EAD files, according to
local guidelines established by UC Riverside Special Collections and
University Archives.

"""
import os
import codecs
import re
import sys
import argparse
from io import BytesIO
import requests
from lxml import etree
from iso639 import languages

def main(args=None):
    """Parse command line arguments.
    Iterate over EAD files to process, validate, & write new file(s).
    """
    parser = argparse.ArgumentParser(
        description="""oac_process takes an EAD file exported from
        ArchivesSpace, does standard edits for upload to OAC, 
        and moves it to the shared drive.""")
    parser.add_argument(
        'files', nargs='*', help="one or more files to process")
    parser.add_argument(
        '--wrca', action='store_true', help="""use --wrca when
        processing WRCA file(s).""")
    parser.add_argument(
        '--in-place', action='store_true', help="""use --in-place if
        you want to process the file where it is, instead of moving it 
        to the standard shared drive location""")
    parser.add_argument(
        '--keep-raw', action='store_true', help="""use --keep-raw if
        you want to keep the original file(s) downloaded from
        ArchivesSpace. Otherwise, they'll be deleted.""")

    #print help if no args given
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args is None:
        args = parser.parse_args()

    for i, value in enumerate(args.files):
        ead_file = args.files[i]
        processed = process(ead_file)
        new_xml = processed[0]
        ead_id = processed[1]

        #ead validation
        validate(new_xml)

        #write out to file
        write_out(ead_file, new_xml, ead_id, args.wrca, args.in_place, args.keep_raw)

def process(ead_file):
    """Return edited EAD, along with its <eadid>.

    ead_file: path to an EAD file
    """
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    xml = etree.parse(ead_file, parser)
    namespace = '{urn:isbn:1-931666-22-9}'

    working_dir = os.path.dirname(os.path.abspath(__file__))
    stylesheet = 'stylesheets/aspace_oac.xslt'
    xsl_file = os.path.join(working_dir, stylesheet)

    #apply xslt (does the majority of processing)
    xslt = etree.parse(xsl_file)
    transform = etree.XSLT(xslt)
    new_xml = transform(xml)

    #strip num tag from titleproper
    numtag = new_xml.find('//{0}titleproper/{0}num'.format(namespace))
    if numtag is not None:
        titleproper = numtag.getparent()
        titleproper.remove(numtag)
        titleproper.text = titleproper.text.strip()

    # ISO markup for <langmaterial> element
    # Example:
    ##<langmaterial>The collection is in <language langcode="eng">English</language>
    langmat = new_xml.find('//{0}archdesc/{0}did/{0}langmaterial'.format(namespace))
    for lang in languages:
        code = lang.bibliographic
        if code != '':
            if lang.name in langmat.text:
                langmarkup = '<language langcode="' + code + r'"\>' +  lang.name + '</language>'
                langmat.text = langmat.text.replace(lang.name, langmarkup, 1)

    #get ead_id to use as filename
    ead_id = new_xml.find('//{0}eadheader/{0}eadid'.format(namespace)).text.strip()

    #to string for regex operations
    new_xml = str(etree.tostring(
        new_xml, pretty_print=True, xml_declaration=True, encoding='UTF-8'
        ), 'utf-8')

    ##remove the namespace declarations within elements
    xmlns = re.compile(
        r'xmlns:xs="http:\/\/www\.w3\.org\/2001\/XMLSchema"\s+xmlns:ead="urn:isbn:1-931666-22-9"')
    new_xml = re.sub(xmlns, '', new_xml)
    #lowercase "linear feet"
    new_xml = re.sub(r'Linear\s+Feet', 'linear feet', new_xml)
    #hacky angle bracket stuff for langmaterial
    #TODO: figure out how to do the markup more elegantly w/ lxml, eliminate need for this
    new_xml = new_xml.replace(r'&lt;/', r'</')
    new_xml = new_xml.replace(r'&lt;', r'<')
    new_xml = new_xml.replace(r'\&gt;', r'>')
    new_xml = new_xml.replace(r'&gt;', r'>')

    return new_xml, ead_id

def validate(xml_string):
    """Validate against EAD schema, print results"""
    #parse string back into lxml
    checkdoc = bytes(xml_string, 'utf-8')
    checkdoc = etree.parse(BytesIO(checkdoc))
    #grab schema from Library of Congress website
    loc = requests.get('https://www.loc.gov/ead/ead.xsd').text
    bytes_schema = BytesIO(bytes(loc, 'utf-8'))
    xmlschema_doc = etree.parse(bytes_schema)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    #evaluate and print validation status
    if xmlschema.validate(checkdoc) is False:
        print('WARNING: EAD validation failed. Check file for errors.')
    else:
        print('EAD validated')

def write_out(ead_path, new_xml, ead_id, wrca, in_place, keep_raw):
    """Write out processed file based on command-line options."""
    filename = os.path.basename(ead_path)
    abs_path = os.path.abspath(ead_path)

    #normalize filename if it matches ArchivesSpace automated naming scheme
    aspace_re = re.compile(r'([A-Za-z0-9\.]+)_[0-9]{8}_[0-9]{6}_UTC__ead\.xml')
    autonamed = aspace_re.match(filename)
    if autonamed is not None:
        filename = ead_id
    #leave other filenames alone
    else:
        pass

    #set outpath
    if in_place is True:
        outdir = os.path.dirname(abs_path)
        outpath = os.path.join(outdir, filename)
    else:
        subdir = ''
        ead_home = "S:/Special Collections/Archives/Collections/"
        if wrca is True:
            subdir = 'WRCA/WRCA_EAD/'
        elif filename.startswith('ms'):
            subdir = 'MS/MS_EAD/'
        elif filename.startswith('ua'):
            subdir = 'UA/UA_EAD/'
        #if it doesn't start with MS or UA, it's probably WRCA even if user didn't specify
        else:
            subdir = 'WRCA/WRCA_EAD/'
        outpath = os.path.join(ead_home, subdir, filename)

    #write out
    with codecs.open(outpath, 'w', 'utf-8') as outfile:
        outfile.write(new_xml)

    #delete original exported file unless specified
    if keep_raw is True:
        pass
    elif in_place is True:
        pass
    else:
        os.remove(abs_path)

    #print confirmation
    print(filename, 'processed')
    print('Location:', outpath)
    sys.stdout.flush()

# main() idiom
if __name__ == "__main__":
    sys.exit(main())
