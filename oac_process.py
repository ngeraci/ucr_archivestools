#!/usr/bin/env python

import os
import codecs
import re
import sys
import argparse
import requests
import git
from lxml import etree
from io import StringIO, BytesIO
from iso639b_dict import iso639

def main(args=None):
    parser = argparse.ArgumentParser(
        description='oac_process takes an EAD file exported from ArchivesSpace and cleans it for upload to OAC')
    parser.add_argument(
        'files', nargs='*', help='one or more files to process')
    parser.add_argument(
        '--wrca', action='store_true', help='use --wrca if you are processing a WRCA file, to make sure it ends up in the right directory')
    parser.add_argument(
        '--keep-raw', action='store_true', help='use --keep-raw if you want to keep the original file downloaded from ArchivesSpace. otherwise it will be deleted')
    if args is None:
        args = parser.parse_args()

    #special WRCA handling since filenames are weird
    isWRCA = args.wrca
    keepRaw = args.keepRaw

    for i, value in enumerate(args.files):
        process(args.files[i], isWRCA, keepRaw)

def process(eadFile, isWRCA, keepRaw):
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    xml = etree.parse(eadFile, parser)
    ns = '{urn:isbn:1-931666-22-9}'
    xslFile = 'stylesheets/aspace_oac.xslt'
    isodict = iso639()
                
    #apply xslt (does the majority of processing)
    xslt = etree.parse(xslFile)
    transform = etree.XSLT(xslt)
    newXML = transform(xml)

    #lxml processing for things i couldn't figure out how to catch in xslt
    #strip num tag from titleproper
    numtag = newXML.find('//{0}titleproper/{0}num'.format(ns))
    if numtag is not None:
        titleproper = numtag.getparent()
        titleproper.remove(numtag)
        titleproper.text = titleproper.text.strip()

    #ISO markup for <langmaterial> element
    #example: <langmaterial>The collection is in <language langcode="eng">English</language>
    langmat = newXML.find('//{0}archdesc/{0}did/{0}langmaterial'.format(ns))
    for langname in isodict.keys():
        try:
            if langname in langmat.text:
                langmarkup = '<language langcode="' + isodict.get(langname) + '"\>' +  langname + '</language>'
                langmat.text = langmat.text.replace(langname, langmarkup, 1)
        except TypeError: #this gets thrown when already has language element as child
            pass

    #to string for regex operations
    newXML = str(etree.tostring(newXML, pretty_print=True, xml_declaration=True, encoding='UTF-8'),'utf-8')

    ##remove the namespace declarations within elements
    newXML = re.sub(r'xmlns:xs="http:\/\/www\.w3\.org\/2001\/XMLSchema"\s+xmlns:ead="urn:isbn:1-931666-22-9"','',newXML)
    #lowercase "linear feet"
    newXML = re.sub(r'Linear\s+Feet','linear feet',newXML)
    #hacky angle bracket stuff for langmaterial
    #want to figure out how to do the markup more elegantly w/ lxml, should eliminate need for this
    newXML = newXML.replace('&lt;/','</')
    newXML = newXML.replace('&lt;','<')
    newXML = newXML.replace('\&gt;','>')
    newXML = newXML.replace('&gt;','>')

    #call xml validation function
    validate(newXML)

    #write out to file
    writeOut(newXML, eadFile, isWRCA)

def validate(xmlString):
    #validate against schema
    #parse string back into lxml
    checkdoc = bytes(xmlString,'utf-8')
    checkdoc = etree.parse(BytesIO(checkdoc))
    #grab schema from Library of Congress website
    loc = requests.get('https://www.loc.gov/ead/ead.xsd').text
    f = BytesIO(bytes(loc,'utf-8'))
    xmlschema_doc = etree.parse(f)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    #evaluate and print validation status
    if xmlschema.validate(checkdoc) == False:
        print('WARNING: EAD validation failed. Check document for errors.')
    else:
        print('EAD validated')

def writeOut(newXML, eadPath, isWRCA, keepRaw):
    filename = os.path.basename(eadPath)
    absolutePath = os.path.abspath(eadPath)

    #normalize filename
    #regular expression to match ArchivesSpace automated naming scheme
    aspaceFileRE = re.compile(r'([A-Za-z0-9\.]+)_[0-9]{8}_[0-9]{6}_UTC__ead\.xml')    
    autonamed = aspaceFileRE.match(filename)
    if autonamed is not None:
        filename = autonamed.group(1).lower().replace('.','') + '.xml'
    #leave other filenames alone
    else:
        pass

    #choose directory
    eadHome = "S:/Special Collections/Archives/Collections/"
    if isWRCA == True:
        subdir = 'WRCA/WRCA_EAD/'
    elif filename.startswith('ms'):
        subdir = 'MS/MS_EAD/'
    elif filename.startswith('ua'):
        subdir = 'UA/UA_EAD/'

    #write out
    outpath = os.path.join(eadHome,subdir,filename)
    with codecs.open(outpath, 'w', 'utf-8') as outfile:
        outfile.write(newXML)

    #delete original exported file unless specified
    if keepRaw == True:
        pass
    else:
        os.remove(absolutePath)


# main() idiom
if __name__ == "__main__":
    sys.exit(main())