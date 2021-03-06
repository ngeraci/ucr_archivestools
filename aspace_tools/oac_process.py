#!/usr/bin/env python
r"""A command line tool for cleaning up EAD files at UCR.

This tool performs a standard set of edits on EAD files, according to
local guidelines established by UC Riverside Special Collections and
University Archives. Its default behavior also moves the files to the
following locations:

* Manuscript Collections:
    "S:\Special Collections\Archives\Collections\MS\MS_EAD\"
* University Archives:
    "S:\Special Collections\Archives\Collections\UA\UA_EAD\"
* Water Resources Collection & Archives:
    "S:\Special Collections\Archives\Collections\WRCA\WRCA_EAD\"
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
    parser.add_argument('files',
                        nargs='*',
                        help="one or more files to process")
    parser.add_argument('--wrca',
                        action='store_true',
                        help="""use --wrca when
        processing WRCA file(s).""")
    parser.add_argument('--in-place',
                        action='store_true',
                        help="""use --in-place if
        you want to process the file where it is, instead of moving it
        to the standard shared drive location""")
    parser.add_argument('--keep-raw',
                        action='store_true',
                        help="""use --keep-raw if
        you want to keep the original file(s) downloaded from
        ArchivesSpace. Otherwise, they'll be deleted.""")
    parser.add_argument('--ignore-validate',
                        action='store_true',
                        help="""use --ignore-validate
        to ignore EAD validation errors.""")

    # print help if no args given
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args is None:
        args = parser.parse_args()

    for i in range(len(args.files)):
        try:
            finding_aid = FindingAid(args.files[i], args.wrca, args.in_place,
                                     args.keep_raw)
            finding_aid.process()
        except OSError:
            print("*ERROR*\nFile not found:", args.files[i])
        except SyntaxError:
            print("*ERROR*\nNot a valid EAD file:", args.files[i])
        if not args.ignore_validate:
            finding_aid.validate()
        finding_aid.write_out()


class FindingAid(object):
    """
    Finding aid object represents an EAD file for an archival finding aid.
    """
    def __init__(self, filename, wrca, in_place, keep_raw):
        self.ead_path = filename
        self.ead_id = None
        self.new_xml = None
        self.wrca = wrca
        self.in_place = in_place
        self.keep_raw = keep_raw

    def process(self):
        """
        Process EAD using XSLT, LXML and some string cleanup.
        Assign processed EAD string to self.new_xml.
        Assign <eadid> element from EAD to self.ead_id.

        """
        def xslt_transform(self):
            """
            Applies XSLT transformation.
            Assigns processed EAD string to self.new_xml.
            """
            parser = etree.XMLParser(resolve_entities=False,
                                     strip_cdata=False,
                                     remove_blank_text=True)
            xml_tree = etree.parse(self.ead_path, parser)

            working_dir = os.path.dirname(os.path.abspath(__file__))
            stylesheet = 'stylesheets/aspace_oac.xslt'
            xsl_file = os.path.join(working_dir, stylesheet)

            xslt = etree.parse(xsl_file)
            transform = etree.XSLT(xslt)
            self.new_xml = transform(xml_tree)

        def lxml_operations(self):
            """
            Perform additional cleanup using pure LXML.
            Updates value of self.new_xml.
            Assigns <eadid> value to self.ead_id.
            """
            namespace = '{urn:isbn:1-931666-22-9}'
            # get <eadid> to use as filename
            self.ead_id = self.new_xml.find(
                '//{0}eadheader/{0}eadid'.format(namespace)).text.strip()

            # strip <num> tag from <titleproper>
            numtag = self.new_xml.find(
                '//{0}titleproper/{0}num'.format(namespace))
            emph = self.new_xml.find(
                '//{0}titleproper//{0}emph'.format(namespace))
            if numtag is not None:
                titleproper = numtag.getparent()
                titleproper.remove(numtag)
                # manage trailing space after removing <num>
                if emph is None:
                    titleproper.text = titleproper.text.strip()
                else:
                    # title starts with <emph> tag
                    emph = self.new_xml.find(
                        '//{0}titleproper//{0}emph'.format(namespace))
                    emph.tail = emph.tail.rstrip()

            # ISO markup for <langmaterial> element, for example:
            # <langmaterial>The collection is in <language langcode="eng">English</language>
            # TODO: Figure out how to do this more cleanly (not a simple fix, may require XSLT):
            #       * https://stackoverflow.com/questions/1973026/insert-tags-in-elementtree-text
            #       * https://kurtraschke.com/2010/09/lxml-inserting-elements-in-text/
            langmaterial = self.new_xml.find(
                '//{0}archdesc/{0}did/{0}langmaterial'.format(namespace))
            if langmaterial.text is not None:
                for lang in languages:
                    code = lang.bibliographic
                    if code != '':
                        if lang.name in langmaterial.text:
                            langmarkup = ('<language langcode="' + code +
                                          r'"\>' + lang.name + '</language>')
                            langmaterial.text = langmaterial.text.replace(
                                lang.name, langmarkup, 1)
            else:
                print('Check <langmaterial> element: possible markup error.')
                sys.stdout.flush()

            # lowercase "Linear Feet" in <extent>
            extent = self.new_xml.find('//{0}extent'.format(namespace))
            if 'Linear Feet' in extent.text:
                extent.text = re.sub(r'Linear\s+Feet', 'linear feet',
                                     extent.text)

            # simple list bug: https://archivesspace.atlassian.net/browse/ANW-275
            ## currently using blunt method to make sure list in arrangement section has type "simple"
            ## (since that's where we normally mean to use unordered lists)
            series_list = self.new_xml.find(
                '//{0}arrangement/{0}list'.format(namespace))
            if series_list:
                series_list.attrib['type'] = 'simple'

            # digital objects
            digital_objects = self.new_xml.findall(
                '//{0}dao'.format(namespace))
            for dao in digital_objects:
                ## remove "xlink:audience" attribute from all DAOs
                ## see https://archivesspace.atlassian.net/browse/ANW-805 (2.5.1 bug)
                dao.attrib.pop('{http://www.w3.org/1999/xlink}audience', None)
                ## remove daodesc sub-element
                dao.remove(dao.find('{0}daodesc'.format(namespace)))

        def string_operations(self):
            """
            Converts self.new_xml to string.
            Performs final tidying.
            """
            # XML to string
            self.new_xml = str(
                etree.tostring(self.new_xml,
                               pretty_print=True,
                               xml_declaration=True,
                               encoding='UTF-8'), 'utf-8')

            # remove namespace declarations within individual elements
            xmlns = re.compile(
                r'xmlns:xs="http:\/\/www\.w3\.org\/2001\/XMLSchema"'
                r'\s+xmlns:ead="urn:isbn:1-931666-22-9"')
            self.new_xml = re.sub(xmlns, '', self.new_xml)

            # unescape angle brackets: fix for hacky <language> markup
            self.new_xml = self.new_xml.replace(r'&lt;/', r'</')
            self.new_xml = self.new_xml.replace(r'&lt;', r'<')
            self.new_xml = self.new_xml.replace(r'\&gt;', r'>')
            self.new_xml = self.new_xml.replace(r'&gt;', r'>')

        xslt_transform(self)
        lxml_operations(self)
        string_operations(self)

    def validate(self):
        """Validates EAD against schema and print results."""
        # parse string back into lxml
        checkdoc = bytes(self.new_xml, 'utf-8')
        checkdoc = etree.parse(BytesIO(checkdoc))

        # get schema from Library of Congress website
        loc = requests.get('https://www.loc.gov/ead/ead.xsd').text
        bytes_schema = BytesIO(bytes(loc, 'utf-8'))
        xmlschema_doc = etree.parse(bytes_schema)
        xmlschema = etree.XMLSchema(xmlschema_doc)

        # evaluate and print validation status
        if xmlschema.validate(checkdoc) is False:
            print('WARNING: EAD validation failed. Check file for errors.')
        else:
            print('EAD validated')

    def write_out(self):
        """Write out processed file based on command-line options."""
        filename = os.path.basename(self.ead_path)
        abs_path = os.path.abspath(self.ead_path)

        # normalize filename if it matches ArchivesSpace automated naming scheme
        aspace_re = re.compile(
            r'([A-Za-z0-9\.]+)_[0-9]{8}_[0-9]{6}_UTC__ead\.xml')
        autonamed = aspace_re.match(filename)
        if autonamed is not None:
            filename = self.ead_id
        # leave other filenames alone
        else:
            pass

        # set outpath
        if self.in_place is True:
            outdir = os.path.dirname(abs_path)
            outpath = os.path.join(outdir, filename)
        else:
            subdir = ''
            ead_home = "S:/Special Collections/Archives/Collections/"
            if self.wrca is True:
                subdir = 'WRCA/WRCA_EAD/'
            elif filename.startswith('ms'):
                subdir = 'MS/MS_EAD/'
            elif filename.startswith('ua'):
                subdir = 'UA/UA_EAD/'
            # if it doesn't start with MS or UA, it's probably WRCA even if user didn't specify
            else:
                subdir = 'WRCA/WRCA_EAD/'
            outpath = os.path.join(ead_home, subdir, filename)

        # write out
        with codecs.open(outpath, 'w', 'utf-8') as outfile:
            outfile.write(self.new_xml)

        # delete original exported file unless specified
        if self.keep_raw is True:
            pass
        elif self.in_place is True:
            pass
        else:
            os.remove(abs_path)

        # print confirmation
        print(filename, 'processed')
        print('Location:', outpath)
        sys.stdout.flush()
